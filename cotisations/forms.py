from django import forms
from .models import Cotisation


class CotisationForm(forms.ModelForm):
    class Meta:
        model = Cotisation
        # On retire 'mois', 'annee', 'date_echeance' et 'statut'
        fields = [
            'membre', 'type_cotisation', 'montant', 'nombre_mois', 
            'date_paiement', 'libelle', 'observation'
        ]
        widgets = {
            'date_paiement': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'observation': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'membre': forms.Select(attrs={'class': 'form-select'}),
            'type_cotisation': forms.Select(attrs={'class': 'form-select'}),
            'montant': forms.NumberInput(attrs={'class': 'form-control'}),
            'nombre_mois': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'Ex: 6'}),
            'libelle': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.date_paiement:
            self.initial['date_paiement'] = self.instance.date_paiement.strftime('%Y-%m-%d')

    def clean(self):
        cleaned = super().clean()
        type_cot = cleaned.get('type_cotisation')
        membre = cleaned.get('membre')

        # Règle du Droit d'adhésion unique
        if type_cot == 'adhesion' and membre:
            if Cotisation.objects.filter(membre=membre, type_cotisation='adhesion').exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("Ce membre a déjà réglé son droit d'adhésion.")

        return cleaned