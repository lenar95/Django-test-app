from django.db import models


class Profile(models.Model):
    name = models.CharField(max_length=200, verbose_name='Имя')
    title = models.CharField(max_length=200, verbose_name='Заголовок/роль')
    description = models.TextField(verbose_name='Описание')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Аватар')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Анкета'
        verbose_name_plural = 'Анкеты'

    def __str__(self) -> str:
        return self.name
