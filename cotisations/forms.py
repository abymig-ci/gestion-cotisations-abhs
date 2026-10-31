from django import forms
from .models import Cotisation


class CotisationForm(forms.ModelForm):
    class Meta:
        model = Cotisation
        fields = [
            'membre', 'type_cotisation', 'montant', 'mois', 'annee',
            'date_echeance', 'date_paiement', 'statut', 'libelle', 'observation'
        ]
        widgets = {
            'date_echeance': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_paiement': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'observation': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'membre': forms.Select(attrs={'class': 'form-select'}),
            'type_cotisation': forms.Select(attrs={'class': 'form-select'}),
            'mois': forms.Select(attrs={'class': 'form-select'}),
            'statut': forms.Select(attrs={'class': 'form-select'}),
            'montant': forms.NumberInput(attrs={'class': 'form-control'}),
            'annee': forms.NumberInput(attrs={'class': 'form-control'}),
            'libelle': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned = super().clean()
        type_cot = cleaned.get('type_cotisation')
        mois = cleaned.get('mois')
        statut = cleaned.get('statut')
        date_paiement = cleaned.get('date_paiement')

        if type_cot == 'mensuelle' and not mois:
            raise forms.ValidationError(
                "Le mois est obligatoire pour une cotisation mensuelle."
            )
        if statut == 'payee' and not date_paiement:
            raise forms.ValidationError(
                "La date de paiement est obligatoire pour une cotisation payée."
            )
        return cleaned