from django.db import models
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from datetime import date
from django.contrib.auth.models import User


class Poste(models.Model):
    # ⬇️ NOUVEAU
    association = models.ForeignKey(
        'cotisations.Association', on_delete=models.CASCADE,
        related_name='postes', null=True, blank=True,
        verbose_name="Association"
    )
    nom = models.CharField(max_length=100)  # ⚠️ unique=True retiré
    
    class Meta:
        ordering = ['nom']
        unique_together = [('association', 'nom')]  # unicité PAR association
        verbose_name = "Poste"
        verbose_name_plural = "Postes"

    def __str__(self):
        return self.nom


class Groupe(models.Model):
    # ⬇️ NOUVEAU
    association = models.ForeignKey(
        'cotisations.Association', on_delete=models.CASCADE,
        related_name='groupes', null=True, blank=True,
        verbose_name="Association"
    )
    nom = models.CharField(max_length=100)  # ⚠️ unique=True retiré
    description = models.TextField(blank=True, help_text="Ex: Section de Daloa...")
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nom']
        unique_together = [('association', 'nom')]  # unicité PAR association
        verbose_name = "Groupe"
        verbose_name_plural = "Groupes"

    def __str__(self):
        return self.nom


class Reunion(models.Model):
    # ⬇️ NOUVEAU
    association = models.ForeignKey(
        'cotisations.Association', on_delete=models.CASCADE,
        related_name='reunions', null=True, blank=True,
        verbose_name="Association"
    )
    titre = models.CharField(max_length=200, help_text="Ex: Réunion de bureau, Assemblée générale...")
    date_reunion = models.DateTimeField()
    lieu = models.CharField(max_length=200)
    groupe = models.ForeignKey(
        Groupe, on_delete=models.CASCADE, related_name='reunions',
        verbose_name="Groupe organisateur"
    )
    description = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_reunion']
        verbose_name = "Réunion"
        verbose_name_plural = "Réunions"

    def __str__(self):
        return f"{self.titre} - {self.date_reunion.strftime('%d/%m/%Y')}"


class Membre(models.Model):
    STATUT_CHOICES = [
        ('actif', 'Actif'),
        ('inactif', 'Inactif'),
        ('suspendu', 'Suspendu'),
    ]
    
    # ⬇️ NOUVEAU
    association = models.ForeignKey(
        'cotisations.Association', on_delete=models.CASCADE,
        related_name='membres', null=True, blank=True,
        verbose_name="Association"
    )
    
    utilisateur = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='membre_profil',
        verbose_name="Compte utilisateur lié"
    )
    
    invitation_token = models.CharField(max_length=100, blank=True, null=True, unique=True)
    invitation_date = models.DateTimeField(blank=True, null=True)
    
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    date_adhesion = models.DateField(default=timezone.now)
    
    poste = models.ForeignKey(
        Poste, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='membres',
        verbose_name="Poste dans l'association"
    )
    
    groupe = models.ForeignKey(
        Groupe, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='membres',
        verbose_name="Groupe d'appartenance"
    )
    
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='actif')

    class Meta:
        ordering = ['nom', 'prenom']
        verbose_name = "Membre"
        verbose_name_plural = "Membres"

    def __str__(self):
        return f"{self.nom} {self.prenom}"

    @property
    def date_fin_carence(self):
        return self.date_adhesion + relativedelta(months=6)

    @property
    def statut_cotisation(self):
        from cotisations.models import Parametre
        
        aujourd_hui = timezone.now().date()
        
        if self.statut == 'inactif':
            return "Inactif"
        if self.statut == 'suspendu':
            return "Suspendu"

        if aujourd_hui < self.date_fin_carence:
            return "En carence"

        if self.cotisations.filter(type_cotisation='exceptionnelle', statut='en_attente').exists():
            return "En retard"

        # ⬇️ MODIFIÉ : on prend les params de CETTE association
        try:
            parametres = Parametre.objects.filter(association_id=self.association_id).first()
        except Exception:
            parametres = None

        if parametres:
            base_calcul = parametres.base_calcul_date
            mois_tolerance = parametres.nombre_mois_tolerance
        else:
            base_calcul = 'derniere_reunion'
            mois_tolerance = 4

        if base_calcul == 'derniere_reunion':
            # ⬇️ MODIFIÉ : réunions de CETTE association
            derniere_reunion = Reunion.objects.filter(
                association_id=self.association_id,
                date_reunion__lte=timezone.now()
            ).order_by('-date_reunion').first()
            if derniere_reunion:
                date_reference = derniere_reunion.date_reunion.date()
            else:
                date_reference = aujourd_hui
        else:
            date_reference = aujourd_hui

        date_limite = date_reference - relativedelta(months=mois_tolerance)

        derniere_cot = self.cotisations.filter(
            type_cotisation='mensuelle', statut='payee'
        ).order_by('-annee', '-mois').first()

        if derniere_cot:
            date_paiement = date(derniere_cot.annee, derniere_cot.mois, 1)
            if date_paiement < date_limite:
                return "En retard"
        else:
            return "En retard"

        return "À jour"


class ProfilAcces(models.Model):
    utilisateur = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profil_acces',
        verbose_name="Utilisateur"
    )
    
    acces_membres = models.BooleanField(default=False, verbose_name="Accès à la gestion des membres")
    acces_cotisations = models.BooleanField(default=False, verbose_name="Accès à la gestion des cotisations")
    acces_depenses = models.BooleanField(default=False, verbose_name="Accès à la gestion des dépenses")
    acces_reunions = models.BooleanField(default=False, verbose_name="Accès à la gestion des réunions")
    acces_groupes = models.BooleanField(default=False, verbose_name="Accès à la gestion des groupes")
    acces_postes = models.BooleanField(default=False, verbose_name="Accès à la gestion des postes")
    acces_parametres = models.BooleanField(default=False, verbose_name="Accès aux paramètres")
    acces_sauvegardes = models.BooleanField(default=False, verbose_name="Accès aux sauvegardes")

    class Meta:
        verbose_name = "Profil d'accès"
        verbose_name_plural = "Profils d'accès"

    def __str__(self):
        return f"Accès de {self.utilisateur.username}"