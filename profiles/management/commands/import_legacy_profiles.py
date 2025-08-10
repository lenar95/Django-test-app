from pathlib import Path
from typing import List, Dict

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings

from profiles.models import Profile


LEGACY_PROFILES: List[Dict[str, str]] = [
    {
        "name": "Царь‑Заказчик",
        "title": "Правитель Технограда",
        "description": (
            "Царь‑Заказчик — мудрый правитель цифрового государства. Он управляет государственным порталом, "
            "следит за тем, чтобы сервисы работали быстро и без сбоев, и всегда стремится улучшить жизнь своих подданных.\n\n"
            "Его корона не только символ власти, но и знак ответственности за судьбу портала. "
            "Вдохновлённый новыми технологиями, он держит руку на пульсе и не боится изменений."
        ),
        "image": "tsar.png",
    },
    {
        "name": "Илья Девопсевич",
        "title": "Девопс‑богатырь",
        "description": (
            "Илья Девопсевич — настоящий богатырь мира инфраструктуры. Он умеет поднимать кластеры, "
            "автоматизировать развёртывания и строить непрерывные пайплайны. Для него нет слишком сложных серверов или запутанных скриптов.\n\n"
            "Когда Илья ударит по клавиатуре, в бой идут контейнеры, оркестраторы и репозитории. "
            "Он знает, что надёжная инфраструктура — основа стабильной работы."
        ),
        "image": "ilya.png",
    },
    {
        "name": "Добрыня Безопасович",
        "title": "Рыцарь безопасности",
        "description": (
            "Добрыня Безопасович — страж цифровой безопасности. Он тщательно хранит пароли, внедряет шифрование "
            "и стоически отбивает атаки. Его зоркий взгляд улавливает подозрительные скрипты издалека.\n\n"
            "Он уверен: доверие пользователей дороже любого золота, а конфиденциальность — священный долг. "
            "С его щитом злоумышленникам не прорваться."
        ),
        "image": "dobrynya.png",
    },
    {
        "name": "Алёша Фронтендов",
        "title": "Мастер интерфейсов",
        "description": (
            "Алёша Фронтендов — волшебник пользовательских интерфейсов. Под его руками кнопки сияют, формы улыбаются, "
            "а пользователи забывают про мануалы. Он умеет говорить с дизайнерами, находить общий язык с кодом и дарит удобство каждому.\n\n"
            "Его работа — чтобы даже бабушка Нюра без труда нашла нужную кнопку и получила то, что ей нужно. "
            "Учитывая потребности людей, он делает технологии доступными."
        ),
        "image": "alyosha.png",
    },
    {
        "name": "Царевна‑Дата",
        "title": "Цифровая принцесса",
        "description": (
            "Царевна‑Дата — олицетворение данных. Её силуэты составлены из потоков информации и блестящих битов. "
            "Она стремится быть структурированной, чистой и доступной для тех, кто умеет бережно с ней обращаться.\n\n"
            "Похищенная Кощем, она стала поводом для подвигов богатырей, ведь данные — важнейшее сокровище цифрового мира. "
            "Её стоит защищать и уважать."
        ),
        "image": "tsarevna.png",
    },
    {
        "name": "Кощей Бессмертный",
        "title": "Владыка монолита",
        "description": (
            "Кощей Бессмертный — хранитель старых систем и монолитов. Его бессмертие прячется в забытых процессах и устаревших лицензиях. "
            "Он не любит, когда что‑то меняют, и удерживает данные в плену.\n\n"
            "Наши герои вступили с ним в схватку, чтобы освободить Царевну‑Дату. Хотя Кощей силён и изворотлив, доверие к нему ограничено: "
            "он хранит лицензионные ключи и не признаёт облака."
        ),
        "image": "koschei.png",
    },
]


class Command(BaseCommand):
    help = "Импортирует старые HTML-анкеты в БД и копирует аватары в MEDIA_ROOT/avatars"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Удалить существующие дубликаты по имени и пересоздать",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        base_dir = Path(settings.BASE_DIR)
        legacy_img_dir = base_dir / "images"
        media_avatars_dir = Path(settings.MEDIA_ROOT) / "avatars"
        media_avatars_dir.mkdir(parents=True, exist_ok=True)

        created, updated = 0, 0

        for data in LEGACY_PROFILES:
            name = data["name"]
            title = data["title"]
            description = data["description"]
            image_name = data["image"]

            qs = Profile.objects.filter(name=name)
            if qs.exists():
                if options.get("force"):
                    qs.delete()
                else:
                    self.stdout.write(self.style.WARNING(f"Пропущено (уже есть): {name}"))
                    continue

            profile = Profile.objects.create(name=name, title=title, description=description)
            created += 1

            src_path = legacy_img_dir / image_name
            if src_path.exists():
                # Copy image into ImageField
                with src_path.open("rb") as f:
                    profile.avatar.save(image_name, File(f), save=True)
            else:
                self.stdout.write(self.style.WARNING(f"Нет файла изображения: {src_path}"))

        self.stdout.write(self.style.SUCCESS(f"Импорт завершён. Создано: {created}, обновлено: {updated}"))


