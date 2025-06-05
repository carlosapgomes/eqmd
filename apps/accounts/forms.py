from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import EqmdCustomUser, UserProfile

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Field, Submit, Div, HTML
from crispy_forms.bootstrap import FormActions


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
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_id = "user-creation-form"
        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-lg-3"
        self.helper.field_class = "col-lg-9"

        self.helper.layout = Layout(
            Fieldset(
                "Account Information",
                Field("username", css_class="form-control"),
                Field("email", css_class="form-control"),
                Field("password1", css_class="form-control"),
                Field("password2", css_class="form-control"),
            ),
            Fieldset(
                "Personal Information",
                Field("first_name", css_class="form-control"),
                Field("last_name", css_class="form-control"),
            ),
            Fieldset(
                "Professional Information",
                Field("profession_type", css_class="form-select"),
                Field("professional_registration_number", css_class="form-control"),
                Field("country_id_number", css_class="form-control"),
                Field("fiscal_number", css_class="form-control"),
                Field("phone", css_class="form-control"),
            ),
            FormActions(Submit("submit", "Register", css_class="btn btn-primary")),
        )


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
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_id = "user-change-form"
        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-lg-3"
        self.helper.field_class = "col-lg-9"

        self.helper.layout = Layout(
            Fieldset(
                "Account Information",
                Field("username", css_class="form-control"),
                Field("email", css_class="form-control"),
                Field("password", css_class="form-control"),
            ),
            Fieldset(
                "Personal Information",
                Field("first_name", css_class="form-control"),
                Field("last_name", css_class="form-control"),
            ),
            Fieldset(
                "Professional Information",
                Field("profession_type", css_class="form-select"),
                Field("professional_registration_number", css_class="form-control"),
                Field("country_id_number", css_class="form-control"),
                Field("fiscal_number", css_class="form-control"),
                Field("phone", css_class="form-control"),
            ),
            FormActions(Submit("submit", "Save Changes", css_class="btn btn-primary")),
        )


class UserProfileForm(forms.ModelForm):
    error_css_class = "is-invalid"
    required_css_class = "required"

    class Meta:
        model = UserProfile
        fields = ("display_name", "bio")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_id = "profile-form"
        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-lg-3"
        self.helper.field_class = "col-lg-9"

        # Add read-only fields from user if instance exists
        if self.instance and self.instance.pk:
            # Add read-only fields from user
            self.fields["email"] = forms.EmailField(
                initial=self.instance.email, disabled=True, required=False
            )
            self.fields["first_name"] = forms.CharField(
                initial=self.instance.first_name, disabled=True, required=False
            )
            self.fields["last_name"] = forms.CharField(
                initial=self.instance.last_name, disabled=True, required=False
            )

            # Update layout to include read-only fields
            self.helper.layout = Layout(
                Fieldset(
                    "User Information",
                    Field("email", css_class="form-control", readonly=True),
                    Field("first_name", css_class="form-control", readonly=True),
                    Field("last_name", css_class="form-control", readonly=True),
                ),
                Fieldset(
                    "Profile Information",
                    Field("display_name", css_class="form-control"),
                    Field("bio", css_class="form-control"),
                ),
                FormActions(
                    Submit("submit", "Update Profile", css_class="btn btn-primary"),
                    HTML(
                        '<a href="{% url \'apps.accounts:profile\' public_id=object.public_id %}" class="btn btn-secondary ms-2">Cancel</a>'
                    ),
                ),
            )
        else:
            # Basic layout for new profiles
            self.helper.layout = Layout(
                Fieldset(
                    "Profile Information",
                    Field("display_name", css_class="form-control"),
                    Field("bio", css_class="form-control"),
                ),
                FormActions(
                    Submit("submit", "Create Profile", css_class="btn btn-primary"),
                    HTML(
                        '<a href="{% url \'apps.accounts:profile\' public_id=object.public_id %}" class="btn btn-secondary ms-2">Cancel</a>'
                    ),
                ),
            )
