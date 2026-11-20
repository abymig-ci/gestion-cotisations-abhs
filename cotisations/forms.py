from django import forms
from .models import Cotisation, Parametre, CotisationLibre


class CotisationForm(forms.ModelForm):
    class Meta:
        model = Cotisation
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
            'montant_cotisation_mensuelle': forms.NumberInput(attrs={'class': 'form-control'}),
            'messages_defilants': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Réunion samedi à 16h\nCotisation de novembre à régler'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if self.instance and self.instance.pk and self.instance.date_paiement:
            self.initial['date_paiement'] = self.instance.date_paiement.strftime('%Y-%m-%d')
        
        if not self.instance.pk:
            parametre, _ = Parametre.objects.get_or_create(id=1)
            self.initial['montant'] = parametre.montant_cotisation_mensuelle

    def clean(self):
        cleaned = super().clean()
        type_cot = cleaned.get('type_cotisation')
        membre = cleaned.get('membre')

        if type_cot == 'adhesion' and membre:
            if Cotisation.objects.filter(membre=membre, type_cotisation='adhesion').exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("Ce membre a déjà réglé son droit d'adhésion.")

        return cleaned


class ParametreForm(forms.ModelForm):
    class Meta:
        model = Parametre
        fields = [
            'logo',
            'nom_association',
            'couleur_principale',
            'base_calcul_date',
            'nombre_mois_tolerance',
            'mois_carence',
            'montant_cotisation_mensuelle',
            'messages_defilants',
            'montants_initiaux_actifs',
            'depenses_initiales',
            'solde_initial',
        ]
        widgets = {
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'nom_association': forms.TextInput(attrs={'class': 'form-control'}),
            'couleur_principale': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}), # <-- SÉLECTEUR DE COULEUR
            'base_calcul_date': forms.Select(attrs={'class': 'form-select'}),
            'nombre_mois_tolerance': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'mois_carence': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 60}),
            'montant_cotisation_mensuelle': forms.NumberInput(attrs={'class': 'form-control'}),
            'messages_defilants': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Réunion samedi à 16h\nCotisation de novembre à régler'}),
            'montants_initiaux_actifs': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'depenses_initiales': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '1'}),
            'solde_initial': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        est_super = bool(user and user.is_superuser)
        if not est_super:
            # La case d'activation est réservée au super utilisateur
            del self.fields['montants_initiaux_actifs']
            # Les autres ne voient les deux montants que si le super utilisateur les a activés
            if not (self.instance and self.instance.pk and self.instance.montants_initiaux_actifs):
                del self.fields['depenses_initiales']
                del self.fields['solde_initial']


class CotisationLibreForm(forms.ModelForm):
    class Meta:
        model = CotisationLibre
        fields = ['motif', 'date_cotisation', 'description']
        widgets = {
            'motif': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Soutien à la famille d\'un membre'}),
            'date_cotisation': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
