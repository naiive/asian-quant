#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import ssl
import smtplib
from typing import List, Optional
import pandas as pd
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email import encoders

from conf.config import SYSTEM_CONFIG, EMAIL_CONFIG
from core.notify.message_builder import build_unified_message

def send_email(
    smtp_host: str,
    smtp_port: int,
    use_ssl: bool,
    username: str,
    password: str,
    sender: str,
    to_list: List[str],
    subject: str,
    body: str,
    attachment_path: Optional[str] = None
) -> bool:
    try:
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = ", ".join([x for x in to_list if x])
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{os.path.basename(attachment_path)}"'
            )
            msg.attach(part)

        if use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
                if username:
                    server.login(username, password)
                server.sendmail(sender, to_list, msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.ehlo()
                try:
                    server.starttls()
                except Exception as e:
                    print(f"❌ [失败] email failed {e}")
                if username:
                    server.login(username, password)
                server.sendmail(sender, to_list, msg.as_string())

        print("📧 [成功] email sent")
        return True
    except Exception as e:
        print(f"❌ [失败] email failed {e}")
        return False

def email_sender(
    df: Optional[pd.DataFrame],
    strategy_name: Optional[str]
) -> None:

    if SYSTEM_CONFIG.get("ENABLE_EMAIL"):
        title_main, body = build_unified_message(df, strategy_name)
        subject = f"[{strategy_name}] {title_main}"
        send_email(
            EMAIL_CONFIG["SMTP_HOST"],
            int(EMAIL_CONFIG.get("SMTP_PORT", 465)),
            EMAIL_CONFIG.get("USE_SSL", True),
            EMAIL_CONFIG["USERNAME"],
            EMAIL_CONFIG["PASSWORD"],
            EMAIL_CONFIG["FROM"],
            EMAIL_CONFIG["TO"],
            subject=subject,
            body=body,
            attachment_path=strategy_name
        )
