from django.db import models
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from datetime import date


class Poste(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    
    class Meta:
        ordering = ['nom']
        verbose_name = "Poste"
        verbose_name_plural = "Postes"

    def __str__(self):
        return self.nom


class Groupe(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, help_text="Ex: Section de Daloa...")
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nom']
        verbose_name = "Groupe"
        verbose_name_plural = "Groupes"

    def __str__(self):
        return self.nom


class Reunion(models.Model):
    titre = models.CharField(max_length=200, help_text="Ex: Réunion de bureau, Assemblée générale...")
    date_reunion = models.DateTimeField()
    lieu = models.CharField(max_length=200)
    groupe = models.ForeignKey(
        Groupe, 
        on_delete=models.CASCADE, 
        related_name='reunions',
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
    
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    date_adhesion = models.DateField(default=timezone.now)
    
    poste = models.ForeignKey(
        Poste, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='membres',
        verbose_name="Poste dans l'association"
    )
    
    groupe = models.ForeignKey(
        Groupe, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='membres',
        verbose_name="Groupe d'appartenance"
    )
    
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='actif'
    )

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
        aujourd_hui = timezone.now().date()
        
        if self.statut == 'inactif':
            return "Inactif"
        if self.statut == 'suspendu':
            return "Suspendu"

        # 1. Période de carence
        if aujourd_hui < self.date_fin_carence:
            return "En carence"

        # 2. Cotisations exceptionnelles impayées
        if self.cotisations.filter(type_cotisation='exceptionnelle', statut='en_attente').exists():
            return "En retard"

        # 3. Cotisations mensuelles par rapport à la dernière réunion passée (TOUS GROUPES CONFONDUS)
        # On cherche la réunion la plus récente qui a DÉJÀ eu lieu
        derniere_reunion = Reunion.objects.filter(date_reunion__lte=timezone.now()).order_by('-date_reunion').first()
        
        if derniere_reunion:
            date_reunion = derniere_reunion.date_reunion.date()
            # La date limite est 3 mois avant la réunion
            date_limite = date_reunion - relativedelta(months=4)
            
            derniere_cot = self.cotisations.filter(
                type_cotisation='mensuelle',
                statut='payee'
            ).order_by('-annee', '-mois').first()

            if derniere_cot:
                date_paiement = date(derniere_cot.annee, derniere_cot.mois, 1)
                # Si le dernier paiement est antérieur à la date limite, il est en retard
                if date_paiement < date_limite:
                    return "En retard"
            else:
                # Aucune mensuelle payée et plus en carence
                return "En retard"
        else:
            # S'il n'y a eu AUCUNE réunion dans l'association pour le moment
            # On vérifie qu'il a payé au moins une fois ce mois-ci ou le mois dernier
            derniere_cot = self.cotisations.filter(type_cotisation='mensuelle', statut='payee').order_by('-annee', '-mois').first()
            if derniere_cot:
                mois_paiement_absolu = derniere_cot.annee * 12 + derniere_cot.mois
                mois_actuel_absolu = aujourd_hui.year * 12 + aujourd_hui.month
                if mois_paiement_absolu < (mois_actuel_absolu - 1):
                    return "En retard"
            else:
                return "En retard"

        return "À jour"
# Version finale du 04/11/2026