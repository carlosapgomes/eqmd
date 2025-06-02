from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import EqmdCustomUser, UserProfile

class EqmdCustomUserCreationForm(UserCreationForm):
    class Meta:
        model = EqmdCustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 
                  'profession_type', 'professional_registration_number',
                  'country_id_number', 'fiscal_number', 'phone')

class EqmdCustomUserChangeForm(UserChangeForm):
    class Meta:
        model = EqmdCustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 
                  'profession_type', 'professional_registration_number',
                  'country_id_number', 'fiscal_number', 'phone')

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('display_name', 'bio')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Add read-only fields from user
            self.fields['email'] = forms.EmailField(
                initial=self.instance.email,
                disabled=True,
                required=False
            )
            self.fields['first_name'] = forms.CharField(
                initial=self.instance.first_name,
                disabled=True,
                required=False
            )
            self.fields['last_name'] = forms.CharField(
                initial=self.instance.last_name,
                disabled=True,
                required=False
            )