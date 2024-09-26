from django.db import models


class TgUser(models.Model):
    # API_TOKEN = '7800525954:AAFcD3dPGBsb9iC8-m76T-iGCoxZKVCkCbg'
    username = models.CharField(max_length=150, null=False, blank=True)
    telegram_id = models.CharField(max_length=50, blank=True, null=True, unique=True)



class BotUser(models.Model):
    STATUS_CHOICES = [
        ("accepted", "Qabul qilingan"),
        ("waiting", "Kutilmoqda"),
        ("canceled", "Bekor qilingan"),
        ("finished", "Tugatilgan"),
    ]
    phone_number = models.CharField(max_length=20)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    tg_user = models.ForeignKey(TgUser, on_delete=models.CASCADE, related_name='insurances')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="waiting")
    passport_front_ids = models.JSONField(default=list, blank=True)
    passport_back_ids = models.JSONField(default=list, blank=True)
    front_tex_passport_ids = models.JSONField(default=list, blank=True)
    back_tex_passport_ids = models.JSONField(default=list, blank=True)
    prava_ids = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Insurance for {self.user.username} - Status: {self.status}"
