"""
byceps.services.bungalow.blueprints.site.forms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2014-2026 Jochen Kupperschmidt
:License: Revised BSD (see `LICENSE` file for details)
"""

from flask import g
from flask_babel import gettext, lazy_gettext
from wtforms import FileField, StringField, TextAreaField
from wtforms.validators import InputRequired, Length, ValidationError

from byceps.services.consent import consent_service, consent_subject_service
from byceps.services.ticketing import ticket_service
from byceps.services.user import user_service
from byceps.util.l10n import LocalizedForm


def validate_user(form, field):
    screen_name = field.data.strip()

    db_user = user_service.find_db_user_by_screen_name(screen_name)

    if db_user is None:
        raise ValidationError(gettext('Unknown username'))

    if not db_user.initialized:
        raise ValidationError(gettext('The user account is not active.'))

    user = user_service.get_user(db_user.id)

    if user.suspended or user.deleted:
        raise ValidationError(gettext('The user account is not active.'))

    required_consent_subjects = (
        consent_subject_service.get_subjects_required_for_brand(g.site.brand_id)
    )
    required_consent_subject_ids = {
        subject.id for subject in required_consent_subjects
    }

    if not consent_service.has_user_consented_to_all_subjects(
        user.id, required_consent_subject_ids
    ):
        raise ValidationError(
            gettext(
                'User "%(screen_name)s" has not yet given all necessary '
                'consents. Logging in again is required.',
                screen_name=user.screen_name,
            )
        )

    # LANresort-specific requirement
    if not _has_full_name_given(user.id):
        raise ValidationError(
            f'"{user.screen_name}" hat keinen Vor- und/oder Nachnamen '
            'angegeben.'
        )

    # LANresort-specific requirement
    if _already_uses_ticket(user.id):
        raise ValidationError(f'"{user.screen_name}" hat bereits einen Platz.')

    field.data = user


def _has_full_name_given(user_id) -> bool:
    detail = user_service.get_detail(user_id)
    return detail.first_name and detail.last_name


def _already_uses_ticket(user_id) -> bool:
    return ticket_service.uses_any_ticket_for_party(user_id, g.party.id)


class OccupantAddForm(LocalizedForm):
    occupant = StringField(
        lazy_gettext('Username'), [InputRequired(), validate_user]
    )


class DescriptionUpdateForm(LocalizedForm):
    title = StringField('Name', validators=[Length(max=20)])
    description = TextAreaField('Beschreibung', validators=[Length(max=4000)])


class AvatarUpdateForm(LocalizedForm):
    image = FileField('Bilddatei', [InputRequired()])
