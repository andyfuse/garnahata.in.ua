import logging

from django.db import models
from django.core.validators import RegexValidator
from django.db import transaction
from django.forms.models import model_to_dict
from django.utils import timezone
from django.core.urlresolvers import reverse

from djgeojson.fields import PointField
from openpyxl import load_workbook

from catalog.exc import ImportException


class Ownership(models.Model):
    owner = models.TextField("Власник")
    asset = models.TextField("Властивості нерухомості")
    registered = models.DateTimeField("Дата реєстрації", blank=True, null=True)
    ownership_ground = models.TextField("Підстава власності", blank=True)
    ownership_form = models.TextField("Форма власності", blank=True)
    share = models.TextField("Частка", blank=True)
    comment = models.TextField("Коментар", blank=True)

    mortgage_registered = models.DateTimeField(
        "Дата реєстрації іпотекі", blank=True, null=True)

    mortgage_charge = models.TextField("Підстава обтяження", blank=True)
    mortgage_details = models.TextField("Деталі за іпотекой", blank=True)
    mortgage_charge_subjects = models.TextField(
        "Суб'єкти обтяження", blank=True)
    mortgage_holder = models.TextField(
        "Заявник або іпотекодержатель", blank=True)
    mortgage_mortgagor = models.TextField(
        "Власник або іпотекодавець", blank=True)
    mortgage_guarantor = models.TextField(
        "Поручитель", blank=True)
    mortgage_other_persons = models.TextField(
        "Інші суб'єкти обтяження", blank=True)

    prop = models.ForeignKey("Property", verbose_name="Власність")

    def __unicode__(self):
        return "%s: %s" % (
            self.owner,
            self.asset)

    def __str__(self):
        return self.__unicode__()

    def to_dict(self, include_address=False, include_name_alternatives=False):
        """
        Convert Ownership model to an indexable presentation for ES.
        """
        d = model_to_dict(self, fields=[
            "id", "owner", "asset", "registered", "ownership_ground",
            "ownership_form", "share", "comment", "mortgage_registered",
            "mortgage_charge", "mortgage_details", "mortgage_charge_subjects",
            "mortgage_holder", "mortgage_mortgagor", "mortgage_guarantor",
            "mortgage_other_persons"])

        if include_address:
            addr = self.prop.address
            d["addr_title"] = addr.title
            d["addr_address"] = addr.address
            d["addr_commercial_name"] = addr.commercial_name
            d["addr_city"] = addr.get_city_display()

        if include_name_alternatives:
            last_name = ""
            first_name = ""
            patronymic = ""
            name_parts = d["owner"].split(None, 3)
            last_name = name_parts[0]

            if len(name_parts) > 1:
                first_name = name_parts[1]

            if len(name_parts) > 2:
                patronymic = name_parts[2]

            d["full_name_suggest"] = {
                "input": [
                    u" ".join([last_name, first_name,
                               patronymic]),
                    u" ".join([first_name,
                               patronymic,
                               last_name]),
                    u" ".join([first_name,
                               last_name])
                ],
                "output": d["owner"]
            }

        d["_id"] = d["id"]
        d["url"] = self.url

        return d

    def get_absolute_url(self):
        return self.prop.address.get_absolute_url() + ("#ownership_%s" % self.pk)

    @property
    def url(self):
        return self.get_absolute_url()

    class Meta:
        verbose_name = u"Власник"
        verbose_name_plural = u"Власники"


class Property(models.Model):
    address = models.ForeignKey("Address", verbose_name="Адреса")

    def to_dict(self):
        """
        Convert Property model to an indexable presentation for ES.
        """

        owners = []
        for owner in self.ownership_set.all():
            owners.append(owner.to_dict())

        return owners

    class Meta:
        verbose_name = u"Об'єкт"
        verbose_name_plural = u"Об'єкти"


KOATUU = {
    1: "Сімферополь",
    5: "Вінниця",
    7: "Луцьк",
    12: "Дніпропетровськ",
    14: "Донецьк",
    18: "Житомир",
    21: "Ужгород",
    23: "Запоріжжя",
    26: "Івано-Франківськ",
    32: "Київ",
    35: "Кіровоград",
    44: "Луганськ",
    46: "Львів",
    48: "Миколаїв",
    51: "Одеса",
    53: "Полтава",
    56: "Рівне",
    59: "Суми",
    61: "Тернопіль",
    63: "Харків",
    65: "Херсон",
    68: "Хмельницький",
    71: "Черкаси",
    73: "Чернівці",
    74: "Чернігів",
    80: "Київ",
    85: "Севастополь"
}


class MarkersQuerySet(models.QuerySet):
    def map_markers(self):
        return [res.map_marker() for res in self]


class Address(models.Model):
    objects = MarkersQuerySet.as_manager()

    title = models.CharField(
        "Коротка адреса", max_length=150)

    slug = models.SlugField("slug", max_length=200)

    address = models.TextField(
        "Адреса", blank=True)

    cadastral_number = models.CharField(
        "Кадастровий номер", blank=True, validators=[
            RegexValidator(
                regex="^\d{10}:\d{2}:\d{3}:0000$",
                message="Кадастровий код не задовільняє формату")],
        max_length=25)

    city = models.IntegerField(
        "Місто", default=80, choices=KOATUU.items())

    commercial_name = models.CharField(
        "Назва комплексу або району", max_length=150, blank=True)

    link = models.URLField(
        "Посилання на сайт забудовника", max_length=1000, blank=True,
        db_index=True)

    coords = PointField(
        "Позиція на мапі", blank=True)

    date_added = models.DateTimeField(
        "Дата додання на сайт",
        default=timezone.now)

    photo = models.ImageField(u"Фото об'єкта", blank=True, upload_to="images")

    def __unicode__(self):
        return u"%s %s" % (
            self.get_city_display(),
            self.title)

    def __str__(self):
        return self.__unicode__()

    def get_absolute_url(self):
        return reverse('address_details', args=[self.slug])

    @property
    def url(self):
        return self.get_absolute_url()

    class Meta:
        verbose_name = u"Адреса"
        verbose_name_plural = u"Адреси"

    def to_dict(self):
        """
        Convert Address model to an indexable presentation for ES.
        """
        d = model_to_dict(self, fields=[
            "id", "title", "address", "cadastral_number", "city",
            "commercial_name", "link", "coords", "date_added"])

        properties = []
        for prop in self.property_set.all():
            properties.append(prop.to_dict())

        d["_id"] = d["id"]
        d["properties"] = properties
        d["url"] = self.url

        return d

    @transaction.atomic
    def import_owners(self, xls_file):
        wb = load_workbook(xls_file, read_only=True)
        ws = wb.active

        self.save()
        self.property_set.all().delete()

        prev_is_blank = True
        prev_owner = ""
        total_imported = 0

        for i, r in enumerate(ws.rows):
            if i == 0:
                continue

            # Файл, Адрес/Номер, Дата, Власник, Нерухомість, Підстава, Форма,
            # Частка, Дата Обт, Причина Обт, Деталі Обт,
            # Заявник або Іпотекодержатель, Власник або Іпотекодавець,
            # Поручитель, Інші суб"єкти ОБТ

            row = [x.value.strip() if isinstance(x.value, str) else x.value
                   for x in r[:15]]

            row = [x if x is not None else "" for x in row]

            (_, _, registered, owner, asset, ownership_ground, ownership_form,
             share, mortgage_registered, mortgage_charge, mortgage_details,
             mortgage_holder, mortgage_mortgagor, mortgage_charge_subjects,
             mortgage_other_persons) = row

            if not any(row):
                prev_is_blank = True
                continue

            if prev_is_blank:
                curr_property = Property(address=self)
                curr_property.save()
                prev_is_blank = False

            if not owner:
                if not prev_owner:
                    raise ImportException(
                        "В строці %s й попередніх до неї не вказан власник"
                        % i)

                owner = prev_owner

            Ownership(
                prop=curr_property,
                registered=registered or None,
                owner=owner,
                asset=asset,
                ownership_ground=ownership_ground,
                ownership_form=ownership_form,
                share=share,
                mortgage_registered=mortgage_registered or None,
                mortgage_charge=mortgage_charge,
                mortgage_details=mortgage_details,
                mortgage_holder=mortgage_holder,
                mortgage_mortgagor=mortgage_mortgagor,
                mortgage_charge_subjects=mortgage_charge_subjects,
                mortgage_other_persons=mortgage_other_persons
            ).save()
            total_imported += 1

            prev_owner = owner

        logging.debug("Imported in total: %s" % total_imported)
        self.date_added = timezone.now()
        self.save()
        return total_imported

    def map_marker(self):
        return {
            # WTF!?
            "coords": self.coords["coordinates"][::-1],
            "title": self.title,
            "commercial_name": self.commercial_name,
            "href": self.get_absolute_url()
        }
