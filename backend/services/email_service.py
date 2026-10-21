import asyncio
from datetime import datetime
from email.message import EmailMessage
from typing import Optional, Any

from aiosmtplib import SMTP

from backend.core.configs import settings

RETRY_ATTEMPTS = settings.EMAIL_RETRY_ATTEMPTS


async def send_email(*, to: str, subject: str, text: str, html: Optional[str] = None) -> dict[str, Any]:

    if not to or not subject or not text:
        raise ValueError("Missing required email fields: to, subject, text")

    msg = EmailMessage()
    msg["From"] = settings.MAIL_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)

    if html:
        msg.add_alternative(html, subtype="html")

    last_error = None

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            async with SMTP(
                hostname=settings.MAIL_SERVER,
                port=settings.MAIL_PORT,
                use_tls=settings.MAIL_SSL_TLS,
                start_tls=settings.MAIL_STARTTLS,
            ) as smtp:
                await smtp.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                await smtp.send_message(msg)

            return {
                "success": True,
                "message": "Email sent successfully",
                "attempt": attempt,
            }

        except Exception as e:
            last_error = e

            if attempt < RETRY_ATTEMPTS:
                delay = min(2 ** (attempt - 1), 5)
                await asyncio.sleep(delay)

    raise RuntimeError(f"Failed to send email after {RETRY_ATTEMPTS} attempts: {last_error}")


def enum_value(value: Any, default: str = "N/A") -> str:
    if value is None:
        return default
    return value.value if hasattr(value, "value") else str(value)


async def send_attendance_correction_notification(
    student_email: str,
    request_data: dict[str, Any],
    is_approved: bool,
    processed_by: str,
) -> dict[str, Any]:
    status = "Approved" if is_approved else "Rejected"
    status_color = "#28a745" if is_approved else "#dc3545"
    final_status_label = "Approved" if is_approved else "Final"

    subject = f"Attendance Correction Request {status}"

    outcome_message=(
        "Your attendance record has been updated accordingly."
        if is_approved
        else "Your attendance record remains unchanged. If you believe this decision is incorrect, please contact your instructor or academic coordinator."
    )

    text = f"""
Dear Student,

Your attendance correction request has been {status.lower()}.

Request Details:
- Module ID: {request_data.get("module_id")}
- Original Status: {enum_value(request_data.get("original_status"))}
- Requested Status: {enum_value(request_data.get("proposed_status"))}
- {final_status_label} Status: {enum_value(request_data.get("approved_status") or request_data.get("proposed_status"))}
- Reason: {request_data.get("reason", "No reason provided")}
- Processed by: {processed_by}
- Processed at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

{outcome_message}

Best regards,
CAMWA System

This is an automated message. Please do not reply to this email.
""".strip()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: {status_color}; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; border: 1px solid #ddd; }}
        .badge {{ background-color: {status_color}; color: white; padding: 5px 10px; border-radius: 5px; }}
        .details {{ background-color: #f9f9f9; padding: 15px; border-left: 4px solid {status_color}; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Attendance Correction Request</h2>
            <span class="badge">{status}</span>
        </div>
        
        <div class="content">
            <p>Dear Student,</p>
            <p>Your attendance correction request has been <strong>{status.lower()}</strong>.</p>
        
            <div class="details">
                <h3>Request Details</h3>
                <ul>
                    <li><strong>Module ID:</strong> {request_data.get("module_id")}</li>
                    <li><strong>Original Status:</strong> {enum_value(request_data.get("original_status"))}</li>
                    <li><strong>Requested Status:</strong> {enum_value(request_data.get("proposed_status"))}</li>
                    <li><strong>{final_status_label} Status: {enum_value(request_data.get("approved_status") or request_data.get("proposed_status"))}</li>
                    <li><strong>Reason:</strong> {request_data.get("reason", "No reason provided")}</li>
                    <li><strong>Processed by:</strong> {processed_by}</li>
                    <li><strong>Processed at:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</li>
                </ul>
            </div>
            
            <p><strong>{outcome_message}</strong></p>
        </div>
        <div class="footer">
            <p>Best regards,<br><strong>CAMWA System</strong></p>
            <p>This is an automated message. Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
""".strip()

    return await send_email(to=student_email, subject=subject, text=text, html=html)


async def send_attendance_request_confirmation(
    student_email: str,
    request_data: dict[str, Any],
    request_id: int,
) -> dict[str, Any]:
    subject = "Attendance Correction Request Submitted Successfully"

    text = f"""
Dear Student,

Your attendance correction request has been submitted and is pending review.

Request Details:
- Request ID: {request_id}
- Module ID: {request_data.get("module_id")}
- Current Status: {enum_value(request_data.get("current_status", "N/A"))}
- Requested Status: {enum_value(request_data.get("proposed_status"))}
- Reason: {request_data.get("reason", "No reason provided")}
- Submitted at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

What happens next:
- Your request will be reviewed by faculty or an academic coordinator.
- You will receive another email notification once your request has been processed.
- Processing may take 1-3 business days.
- You can view the status of your request in the CAMWA system.
If you have urgent concerns, please contact your instructor directly.
Best regards,
CAMWA System
This is an automated message. Please do not reply to this email.
""".strip()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; border: 1px solid #ddd; }}
        .badge {{ background-color: #ffc107; color: #212529; padding: 5px 10px; border-radius: 5px; font-weight: bold; }}
        .details {{ background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0; }}
        .info-box {{ background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
        .request-id {{ font-family: monospace; background-color: #f1f1f1; padding: 2px 5px; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Attendance Correction Request</h2>
            <span class="badge">Submitted Successfully</span>
        </div>
        <div class="content">
            <p>Dear Student,</p>
            <p>Your attendance correction request has been <strong>submitted successfully</strong> and is now pending review.</p>
            <div class="details">
                <h3>Request Details</h3>
                <ul>
                    <li><strong>Request ID:</strong> <span class="request-id">#{request_id}</span></li>
                    <li><strong>Module ID:</strong> {request_data.get("module_id")}</li>
                    <li><strong>Current Status:</strong> {enum_value(request_data.get("current_status", "N/A"))}</li>
                    <li><strong>Requested Status:</strong> {enum_value(request_data.get("proposed_status"))}</li>
                    <li><strong>Reason:</strong> {request_data.get("reason", "No reason provided")}</li>
                    <li><strong>Submitted at:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</li>
                </ul>
            </div>
            <div class="info-box">
                <h4>What happens next?</h4>
                <ul>
                    <li>Your request will be reviewed by faculty or an academic coordinator.</li>
                    <li>You will receive another email notification once processed.</li>
                    <li>Processing may take 1-3 business days.</li>
                    <li>You can check the status anytime in the CAMWA system.</li>
                </ul>
            </div>
            <p><strong>Note:</strong> If you have urgent concerns, please contact your instructor directly.</p>
        </div>
        <div class="footer">
            <p>Best regards,<br><strong>CAMWA System</strong></p>
            <p>This is an automated message. Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
""".strip()

    return await send_email(to=student_email, subject=subject, text=text, html=html)

