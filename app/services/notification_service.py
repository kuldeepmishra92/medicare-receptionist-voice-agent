"""
Notification Service — Handles SMS (Twilio), WhatsApp (Twilio WhatsApp API), and Email (Resend/SMTP).
Supports both live API delivery and smart mock logging when API keys are omitted.
"""
from typing import Optional
from loguru import logger

from app.config import settings


class NotificationService:
    """Handles multi-channel notifications for appointment booking, rescheduling, and cancellation."""

    def __init__(self):
        self.twilio_enabled = bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN)
        self.resend_enabled = bool(settings.RESEND_API_KEY)
        self.twilio_client = None

        if self.twilio_enabled:
            try:
                from twilio.rest import Client as TwilioClient
                self.twilio_client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                logger.info("📱 Twilio Client initialized for SMS & WhatsApp.")
            except Exception as e:
                logger.warning(f"⚠️ Twilio Client initialization failed: {e}")
                self.twilio_enabled = False

        if self.resend_enabled:
            try:
                import resend
                resend.api_key = settings.RESEND_API_KEY
                logger.info("📧 Resend Email Client initialized.")
            except Exception as e:
                logger.warning(f"⚠️ Resend Client initialization failed: {e}")
                self.resend_enabled = False

    async def send_sms(self, to: str, message: str) -> bool:
        """Send SMS via Twilio."""
        if not to:
            return False

        if self.twilio_enabled and self.twilio_client and settings.TWILIO_PHONE_NUMBER:
            try:
                self.twilio_client.messages.create(
                    body=message,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=to,
                )
                logger.info(f"📱 Sent SMS to {to}: '{message}'")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to send SMS to {to}: {e}")

        logger.info(f"📱 [MOCK SMS] To: {to} | Message: '{message}'")
        return True

    async def send_whatsapp(self, to: str, message: str) -> bool:
        """Send WhatsApp text via Twilio WhatsApp API."""
        if not to:
            return False

        whatsapp_from = settings.TWILIO_WHATSAPP_NUMBER or "whatsapp:+14155238886"
        to_formatted = to if to.startswith("whatsapp:") else f"whatsapp:{to}"

        if self.twilio_enabled and self.twilio_client:
            try:
                self.twilio_client.messages.create(
                    body=message,
                    from_=whatsapp_from,
                    to=to_formatted,
                )
                logger.info(f"💬 Sent WhatsApp to {to_formatted}: '{message}'")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to send WhatsApp to {to_formatted}: {e}")

        logger.info(f"💬 [MOCK WhatsApp] To: {to_formatted} | Message: '{message}'")
        return True

    async def send_email(self, to: str, subject: str, html_body: str) -> bool:
        """Send HTML Email via Resend or SMTP."""
        if not to:
            return False

        if self.resend_enabled:
            try:
                import resend
                from_email = settings.FROM_EMAIL if (settings.FROM_EMAIL and "@yourdomain.com" not in settings.FROM_EMAIL and "@yourapp.com" not in settings.FROM_EMAIL) else "onboarding@resend.dev"
                resend.Emails.send({
                    "from": from_email,
                    "to": to,
                    "subject": subject,
                    "html": html_body,
                })
                logger.info(f"📧 Sent Email to {to} | Subject: '{subject}'")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to send Email via Resend to {to}: {e}")

        logger.info(f"📧 [MOCK EMAIL] To: {to} | Subject: '{subject}'")
        return True

    async def send_appointment_confirmation(
        self,
        patient_name: str,
        phone: Optional[str],
        email: Optional[str],
        doctor_name: str,
        specialization: str,
        date_str: str,
        time_str: str,
        appointment_id: str,
    ):
        """Send appointment booking confirmation via SMS, WhatsApp, and Email."""
        sms_msg = (
            f"Dear {patient_name}, your appointment with {doctor_name} ({specialization}) "
            f"is CONFIRMED for {date_str} at {time_str}. Appointment ID: {appointment_id}."
        )

        whatsapp_msg = (
            f"🏥 *Appointment Confirmation*\n\n"
            f"Dear *{patient_name}*,\n"
            f"Your appointment has been successfully booked.\n\n"
            f"📋 *Appointment ID:* {appointment_id}\n"
            f"👨‍⚕️ *Doctor:* {doctor_name} ({specialization})\n"
            f"📅 *Date:* {date_str}\n"
            f"⏰ *Time:* {time_str}\n\n"
            f"Thank you for choosing our hospital!"
        )

        email_html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 680px; margin: 0 auto; color: #111111; line-height: 1.5;">
            <h2 style="margin: 0 0 8px 0; color: #111111;">Appointment Confirmation</h2>
            <p>Dear <strong>{patient_name}</strong>,</p>
            <p>Your appointment has been scheduled successfully. Please find the confirmed details below.</p>
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0; border: 1px solid #dddddd;">
                <tr><th style="text-align: left; padding: 10px; border: 1px solid #dddddd; background: #f5f5f5;">Appointment ID</th><td style="padding: 10px; border: 1px solid #dddddd;">{appointment_id}</td></tr>
                <tr><th style="text-align: left; padding: 10px; border: 1px solid #dddddd; background: #f5f5f5;">Patient Name</th><td style="padding: 10px; border: 1px solid #dddddd;">{patient_name}</td></tr>
                <tr><th style="text-align: left; padding: 10px; border: 1px solid #dddddd; background: #f5f5f5;">Doctor</th><td style="padding: 10px; border: 1px solid #dddddd;">{doctor_name}</td></tr>
                <tr><th style="text-align: left; padding: 10px; border: 1px solid #dddddd; background: #f5f5f5;">Doctor Type</th><td style="padding: 10px; border: 1px solid #dddddd;">{specialization}</td></tr>
                <tr><th style="text-align: left; padding: 10px; border: 1px solid #dddddd; background: #f5f5f5;">Date</th><td style="padding: 10px; border: 1px solid #dddddd;">{date_str}</td></tr>
                <tr><th style="text-align: left; padding: 10px; border: 1px solid #dddddd; background: #f5f5f5;">Time</th><td style="padding: 10px; border: 1px solid #dddddd;">{time_str}</td></tr>
                <tr><th style="text-align: left; padding: 10px; border: 1px solid #dddddd; background: #f5f5f5;">Status</th><td style="padding: 10px; border: 1px solid #dddddd;">Confirmed</td></tr>
            </table>
            <p>Please arrive 10 minutes before your scheduled time.</p>
            <p style="margin-top: 24px;">Regards,<br><strong>Hospital Appointment Desk</strong></p>
        </div>
        """

        if phone:
            await self.send_sms(phone, sms_msg)
            await self.send_whatsapp(phone, whatsapp_msg)
        if email:
            await self.send_email(email, f"Appointment Confirmed: {appointment_id}", email_html)

    async def send_appointment_reschedule(
        self,
        patient_name: str,
        phone: Optional[str],
        email: Optional[str],
        doctor_name: str,
        date_str: str,
        time_str: str,
        appointment_id: str,
    ):
        """Send appointment reschedule notification."""
        msg = f"Dear {patient_name}, your appointment {appointment_id} with {doctor_name} has been RESCHEDULED to {date_str} at {time_str}."
        if phone:
            await self.send_sms(phone, msg)
            await self.send_whatsapp(phone, f"🔄 *Appointment Rescheduled*\n\n{msg}")
        if email:
            await self.send_email(email, f"Appointment Rescheduled: {appointment_id}", f"<p>{msg}</p>")

    async def send_appointment_cancellation(
        self,
        patient_name: str,
        phone: Optional[str],
        email: Optional[str],
        doctor_name: str,
        date_str: str,
        time_str: str,
        appointment_id: str,
        reason: Optional[str] = None,
    ):
        """Send appointment cancellation notification."""
        reason_txt = f" (Reason: {reason})" if reason else ""
        msg = f"Dear {patient_name}, your appointment {appointment_id} with {doctor_name} on {date_str} at {time_str} has been CANCELLED{reason_txt}."
        if phone:
            await self.send_sms(phone, msg)
            await self.send_whatsapp(phone, f"❌ *Appointment Cancelled*\n\n{msg}")
        if email:
            await self.send_email(email, f"Appointment Cancelled: {appointment_id}", f"<p>{msg}</p>")


# Global singleton instance
notification_service = NotificationService()

