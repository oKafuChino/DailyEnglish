from aiogram import Router

from app.bot.middlewares.registration import RegistrationMiddleware

router = Router(name="user")
router.message.middleware(RegistrationMiddleware())
