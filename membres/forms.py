from django import forms
from .models import Membre, Groupe, Poste


class MembreForm(forms.ModelForm):
    class Meta:
        model = Membre
        fields = ['nom', 'prenom', 'telephone', 'email', 'groupe', 'date_adhesion', 'poste', 'statut']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: KOUASSI'}),
            'prenom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Jean'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 0102030405'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Ex: jean@email.com'}),
            # Ajout de format='%Y-%m-%d' pour forcer le format HTML5
            'date_adhesion': forms.DateInput(
                format='%Y-%m-%d', 
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'poste': forms.Select(attrs={'class': 'form-select'}),
            'groupe': forms.Select(attrs={'class': 'form-select'}),
            'statut': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On s'assure que la date est au bon format si on modifie un membre existant
        if self.instance and self.instance.pk and self.instance.date_adhesion:
            self.initial['date_adhesion'] = self.instance.date_adhesion.strftime('%Y-%m-%d')
        
        # Afficher "Sans groupe" par défaut si aucun groupe n'est sélectionné
        self.fields['groupe'].empty_label = "Sans groupe"


class GroupeForm(forms.ModelForm):
    class Meta:
        model = Groupe
        fields = ['nom', 'description']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Issia-Saïoua'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PosteForm(forms.ModelForm):
    class Meta:
        model = Poste
        fields = ['nom']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Président(e)'}),
        }