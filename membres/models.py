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
        
        if self.statut != 'actif':
            return "Non applicable"

        # --- 1. PÉRIODE DE CARENCE (6 MOIS) ---
        if aujourd_hui < self.date_fin_carence:
            return "En carence"

        # --- 2. COTISATIONS EXCEPTIONNELLES IMPAYÉES ---
        a_des_exceptionnelles_impayees = self.cotisations.filter(
            type_cotisation='exceptionnelle',
            statut='en_attente'
        ).exists()
        
        if a_des_exceptionnelles_impayees:
            return "En retard"

        # --- 3. COTISATIONS MENSUELLES (vs Dernière réunion du groupe) ---
        if self.groupe:
            derniere_reunion = self.groupe.reunions.order_by('-date_reunion').first()
            if derniere_reunion:
                date_reunion = derniere_reunion.date_reunion.date()
                # La date limite est 3 mois avant la réunion
                date_limite = date_reunion - relativedelta(months=3)
                
                # Dernière cotisation mensuelle payée
                derniere_cot = self.cotisations.filter(
                    type_cotisation='mensuelle',
                    statut='payee'
                ).order_by('-annee', '-mois').first()

                if derniere_cot:
                    date_paiement = date(derniere_cot.annee, derniere_cot.mois, 1)
                    if date_paiement < date_limite:
                        return "En retard"
                else:
                    # Aucune mensuelle payée et plus en carence
                    return "En retard"

        return "À jour"
# Version finale du 04/11/2026