from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import EqmdCustomUser, UserProfile


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
        fields = ("display_name", "bio")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
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
        
        # Apply Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
