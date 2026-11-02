from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import EqmdCustomUser, UserProfile
from .services.team_membership import eligible_specialty_queryset


class EqmdCustomUserCreationForm(UserCreationForm):
    error_css_class = "is-invalid"
    required_css_class = "required"

    class Meta:
        model = EqmdCustomUser
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "profession_type",
            "professional_registration_number",
            "country_id_number",
            "fiscal_number",
            "phone",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control' if field_name != 'profession_type' else 'form-select'
            })


class EqmdCustomUserChangeForm(UserChangeForm):
    error_css_class = "is-invalid"
    required_css_class = "required"

    class Meta:
        model = EqmdCustomUser
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "profession_type",
            "professional_registration_number",
            "country_id_number",
            "fiscal_number",
            "phone",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name != 'password':
                field.widget.attrs.update({
                    'class': 'form-control' if field_name != 'profession_type' else 'form-select'
                })


class UserProfileForm(forms.ModelForm):
    error_css_class = "is-invalid"
    required_css_class = "required"

    class Meta:
        model = UserProfile
        fields = ("display_name", "bio", "current_specialty")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter current_specialty to active memberships in active specialties
        if self.instance and self.instance.user:
            self.fields['current_specialty'].queryset = (
                eligible_specialty_queryset(self.instance.user)
            )
            self.fields['current_specialty'].empty_label = "Selecionar especialidade..."

            # Apply form-select class to current_specialty
            self.fields['current_specialty'].widget.attrs.update({'class': 'form-select'})

        # Add read-only fields from user if instance exists
        if self.instance and self.instance.pk:
            self.fields["email"] = forms.EmailField(
                initial=self.instance.email, disabled=True, required=False
            )
            self.fields["first_name"] = forms.CharField(
                initial=self.instance.first_name, disabled=True, required=False
            )
            self.fields["last_name"] = forms.CharField(
                initial=self.instance.last_name, disabled=True, required=False
            )

        # Apply Bootstrap classes to all other fields
        for field_name, field in self.fields.items():
            if field_name != 'current_specialty':
                field.widget.attrs.update({'class': 'form-control'})
