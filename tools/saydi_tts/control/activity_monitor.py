# -*- coding: utf-8 -*-
"""SAYDI Control activity monitor.

Separate operator commands, scheduler health and actual media processing.
Do not label a regular scheduler tick as render/QC progress.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path

DATE_PREFIX = re.compile(r"^\[(\d{4}-\d\d-\d\d[ T]\d\d:\d\d:\d\d)\]\s*")
LOG_LIMIT = 20

def parsed_time(raw):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z","+00:00")).astimezone()
    except (TypeError, ValueError, OSError):
        return None

def file_date(path):
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).astimezone()
    except OSError:
        return None

def short_tail(path, count=9):
    """Small tail reads on demand; never stream unbounded logs."""
    try:
        with path.open("rb") as handle:
            handle.seek(0,2)
            handle.seek(max(0, handle.tell()-12000))
            lines=handle.read().decode("utf-8",errors="replace").splitlines()
        return [line.strip()[:450] for line in lines if line.strip()][-count:]
    except OSError:
        return []

def append(entries, group, message, instant, kind, seq):
    entries.append({"group":group,"text":str(message)[:400],
                    "time":instant.isoformat(timespec="seconds") if instant else None,
                    "kind":kind,"seq":seq})

def summarize(job, job_path, guardian_log, controller_log, work_log,
              chapter, available_gb, active_processes, now=None):
    now=now or datetime.now().astimezone()
    events=[]
    serial=0
    def event(group, message, when, kind):
        nonlocal serial
        serial+=1
        append(events,group,message,when,kind,serial)

    heartbeat=file_date(guardian_log)
    watchdog_age=int((now-heartbeat).total_seconds()) if heartbeat else None
    watchdog_ok=watchdog_age is not None and 0<=watchdog_age<8*60
    job_state=str(job.get("state") or "NONE")
    action=str(job.get("action") or "")
    chapter_id=job.get("chapter")
    label={"improve":"Tự sửa phát âm","recheck":"Kiểm tra lại QC",
           "resume":"Tiếp tục/tạo chương"}.get(action,action)
    current_check=parsed_time(job.get("last_check_at")) or file_date(job_path)
    last_started=parsed_time(job.get("started_at"))
    last_job_end=parsed_time(job.get("finished_at"))

    if job.get("id"):
        queued=parsed_time(job.get("queued_at"))
        event("Lệnh của Owner",
              f"Đã nhận lệnh {label}, chương {chapter_id}. ID {job['id']}; chưa có nghĩa là đã chạy.",
              queued,"command")
        if last_started:
            event("Lệnh của Owner",
                  f"Tiến trình chương {chapter_id} bắt đầu lần {job.get('attempts',1)}.",
                  last_started,"work")
        if last_job_end:
            event("Lệnh của Owner",
                  f"Lần xử lý kết thúc, mã={job.get('exit_code','?')}, trạng thái={job_state}.",
                  last_job_end,"work")
        if current_check:
            reason = {
                "QUEUED_RESOURCE":f"RAM còn {job.get('last_check_free_ram_gb', job.get('free_ram_gb',available_gb))} GB, chưa đủ 2,3 GB để tải mô hình. Giữ nguyên job.",
                "WAIT_OTHER_WORKER":"Có tác vụ SAYDI nặng khác; đang chờ, không chạy chồng.",
                "QUEUED":"Đã xếp hàng, chưa bắt đầu xử lý.",
                "RUNNING":"Bộ điều phối đang giám sát tiến trình đã giao.",
                "FAILED":"Lượt xử lý thất bại; xem log công việc.",
                "DONE":"Lượt xử lý kết thúc, vẫn cần Owner duyệt âm thanh.",
            }.get(job_state,f"Trạng thái {job_state}.")
            event("Kiểm tra lệnh",reason,current_check,"check")
    if heartbeat:
        word=("Đang kiểm tra định kỳ" if watchdog_ok else "MẤT nhịp kiểm tra định kỳ")
        event("Bộ điều phối",f"{word}. Đây KHÔNG phải bằng chứng đang render/QC.",
              heartbeat,"heartbeat")

    # The current job's dedicated log and relevant selected chapter log have
    # priority over old Chapter 1 R2 logs. Exclude no-op/watchdog repetitions.
    sources=[("Lệnh xử lý",work_log,7),
             (f"Chương {chapter}", (Path(r"D:\SAYDI\OWNER_APPROVED_NATURAL_V5")/
                                f"Chuong_{chapter:02d}"/"job.log"),7),
             ("Lệnh được nhận",controller_log,5)]
    for group,path,count in sources:
        if not path:
            continue
        modified=file_date(path)
        for line in short_tail(path,count):
            if "Completed QC previously; no duplicate work" in line or "TICK_END" in line:
                continue
            match=DATE_PREFIX.match(line)
            timestamp=parsed_time(match.group(1)) if match else modified
            event(group,line,timestamp,"work" if group!="Lệnh được nhận" else "command")
    events.sort(key=lambda e:(e["time"] or "",e["seq"]),reverse=True)
    ordered=[]
    seen=set()
    for e in events:
        key=(e["group"],e["time"],e["text"])
        if key not in seen:
            seen.add(key)
            ordered.append(e)
        if len(ordered)>=LOG_LIMIT:
            break

    has_active=bool(active_processes)
    if has_active:
        category="running"
        headline="ĐANG CÓ TIẾN TRÌNH ÂM THANH THỰC TẾ"
        explanation=("Đã tìm thấy tiến trình render/QC/sửa âm thanh; kiểm tra PID và chương."
                     " Không suy ra tác vụ mới đã khởi chạy chỉ từ trạng thái xếp hàng.")
    elif job_state=="QUEUED_RESOURCE":
        category="waiting"
        headline=f"CHỜ RAM — {label} chương {chapter_id}"
        explanation=(f"Lệnh chưa được thực thi. RAM hiện {available_gb:.2f} GB, "
                     f"ngưỡng tối thiểu 2,3 GB; robot tự kiểm tra lại theo lịch.")
    elif job_state=="WAIT_OTHER_WORKER":
        category="waiting"
        headline="CHỜ TÁC VỤ KHÁC KẾT THÚC"
        explanation="Lệnh chưa chạy; bộ điều phối đang tránh xung đột."
    elif job_state=="QUEUED":
        category="waiting"
        headline="ĐÃ XẾP HÀNG — CHƯA KHỞI CHẠY"
        explanation="Chờ lượt kiểm tra tài nguyên và thực thi."
    elif job_state=="RUNNING":
        category="error"
        headline="BÁO RUNNING NHƯNG KHÔNG CÓ TIẾN TRÌNH"
        explanation="Checkpoint cho biết đang chạy, nhưng không tìm thấy process. Kiểm tra log và Task Scheduler."
    elif job_state=="FAILED":
        category="error"
        headline="LỆNH THẤT BẠI"
        explanation=job.get("detail","Cần xem nhật ký chi tiết.")
    elif job_state=="DONE":
        category="done"
        headline="XONG LƯỢT XỬ LÝ — CHƯA PHẢI FINAL"
        explanation="Kiểm tra file REVIEW và chất lượng trước khi nghiệm thu."
    else:
        category="idle"
        headline="KHÔNG CÓ TÁC VỤ SẢN XUẤT ĐANG CHẠY"
        explanation="Control đang theo dõi; chưa có lệnh render/QC mới."
    if not watchdog_ok:
        headline = "MẤT NHỊP GIÁM SÁT" if not has_active else headline
        explanation += " Không nhận được heartbeat của bộ điều phối trong 8 phút gần đây."
        if not has_active:
            category="error"

    return {"category":category,"headline":headline,"explanation":explanation,
            "scheduler_healthy":watchdog_ok,
            "last_heartbeat":heartbeat.isoformat(timespec="seconds") if heartbeat else None,
            "seconds_since_heartbeat":watchdog_age,
            "last_check":current_check.isoformat(timespec="seconds") if current_check else None,
            "last_processing_started":last_started.isoformat(timespec="seconds") if last_started else None,
            "job_state":job_state,
            "events":ordered,"last_event":ordered[0]["time"] if ordered else None}
