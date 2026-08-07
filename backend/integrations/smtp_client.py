"""Envoi SMTP réel, exécuté dans un thread pour ne pas bloquer FastAPI."""

from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage

from config import settings

logger = logging.getLogger(__name__)


class SMTPConfigurationError(RuntimeError):
    """SMTP est demandé mais ses paramètres sont incomplets."""


class SMTPDeliveryError(RuntimeError):
    """Le serveur SMTP a refusé l'envoi ou n'a pas pu être joint."""


class SMTPClient:
    @property
    def configured(self) -> bool:
        return bool(settings.SMTP_HOST and settings.SMTP_FROM)

    def _send_sync(self, recipient: str, subject: str, body: str) -> None:
        if not self.configured:
            raise SMTPConfigurationError("SMTP est activé mais SMTP_HOST et SMTP_FROM sont requis.")
        if not recipient:
            raise SMTPConfigurationError(
                "Aucun destinataire: ticket.user_email ou SMTP_RECIPIENT est requis."
            )
        if settings.SMTP_USERNAME and not settings.SMTP_PASSWORD:
            raise SMTPConfigurationError(
                "SMTP_PASSWORD est requis lorsque SMTP_USERNAME est renseigné."
            )

        message = EmailMessage()
        message["From"] = settings.SMTP_FROM
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        context = ssl.create_default_context()
        try:
            if settings.SMTP_USE_TLS:
                with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context, timeout=30) as server:
                    if settings.SMTP_USERNAME:
                        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    server.send_message(message)
                return

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
                server.ehlo()
                if settings.SMTP_USE_STARTTLS:
                    server.starttls(context=context)
                    server.ehlo()
                if settings.SMTP_USERNAME:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            logger.exception("Echec de l'envoi SMTP vers %s", recipient)
            raise SMTPDeliveryError(f"Echec de l'envoi SMTP vers {recipient}: {exc}") from exc

    async def send(self, recipient: str, subject: str, body: str) -> None:
        if not settings.SMTP_ENABLED:
            raise SMTPConfigurationError("SMTP_ENABLED=false : aucun e-mail réel ne sera envoyé.")
        await asyncio.to_thread(self._send_sync, recipient, subject, body)
        logger.info("E-mail SMTP envoyé à %s", recipient)
