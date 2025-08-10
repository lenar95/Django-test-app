from django import forms
from .models import Profile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['name', 'title', 'description', 'avatar']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Имя'}),
            'title': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Роль'}),
            'description': forms.Textarea(attrs={'class': 'textarea', 'rows': 5, 'placeholder': 'Описание'}),
        }

