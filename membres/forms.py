from django import forms
from .models import Membre


class MembreForm(forms.ModelForm):
    class Meta:
        model = Membre
        fields = ['nom', 'prenom', 'telephone', 'email', 'date_adhesion', 'poste', 'statut']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: KOUASSI'}),
            'prenom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Jean'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 0102030405'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Ex: jean@email.com'}),
            'date_adhesion': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'poste': forms.Select(attrs={'class': 'form-select'}),
            'statut': forms.Select(attrs={'class': 'form-select'}),
        }