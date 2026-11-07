from django import forms
from .models import Depense

class DepenseForm(forms.ModelForm):
    class Meta:
        model = Depense
        fields = ['libelle', 'montant', 'date_depense', 'categorie', 'membre', 'description']
        widgets = {
            'libelle': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Soutien à un membre'}),
            'montant': forms.NumberInput(attrs={'class': 'form-control'}),
            'date_depense': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'categorie': forms.Select(attrs={'class': 'form-select'}),
            'membre': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.date_depense:
            self.initial['date_depense'] = self.instance.date_depense.strftime('%Y-%m-%d')