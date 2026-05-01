from __future__ import annotations

import factory

from apps.categories.models import Category
from apps.users.tests.factories import UserFactory


class SystemCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"System Category {n}")
    is_system = True
    owner = None


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"User Category {n}")
    is_system = False
    owner = factory.SubFactory(UserFactory)
    parent = None
