from django.db import models
from django.utils import timezone
from membres.models import Membre


class Association(models.Model):
    nom = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='logos_associations/', blank=True, null=True)
    couleur_principale = models.CharField(max_length=7, default="#0a1c5c")
    est_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Association"
        verbose_name_plural = "Associations"

    def __str__(self):
        return self.nom


class Cotisation(models.Model):
    TYPE_CHOICES = [
        ('mensuelle', 'Mensuelle'),
        ('exceptionnelle', 'Exceptionnelle'),
        ('adhesion', "Droit d'adhésion"),
    ]
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('payee', 'Payée'),
        ('retard', 'En retard'),
    ]
    MOIS_CHOICES = [
        (1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'),
        (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'),
        (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre'),
    ]

    # ⬇️ NOUVEAU : Lien avec l'association
    association = models.ForeignKey(
        Association, on_delete=models.CASCADE,
        related_name='cotisations',
        null=True, blank=True,
        verbose_name="Association"
    )

    membre = models.ForeignKey(
        Membre,
        on_delete=models.CASCADE,
        related_name='cotisations'
    )
    type_cotisation = models.CharField(max_length=20, choices=TYPE_CHOICES)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    mois = models.IntegerField(choices=MOIS_CHOICES, null=True, blank=True)
    annee = models.IntegerField(default=timezone.now().year)
    
    nombre_mois = models.IntegerField(
        null=True, blank=True,
        help_text="Remplir si le membre paie plusieurs mois d'avance"
    )
    
    date_echeance = models.DateField()
    date_paiement = models.DateField(null=True, blank=True)
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='en_attente'
    )
    libelle = models.CharField(
        max_length=200, blank=True,
        help_text="Pour les cotisations exceptionnelles"
    )
    observation = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-annee', '-mois', '-date_creation']
        verbose_name = "Cotisation"
        verbose_name_plural = "Cotisations"

    def __str__(self):
        if self.type_cotisation == 'mensuelle':
            return f"{self.membre} - {self.get_mois_display()} {self.annee} - {self.montant} FCFA"
        return f"{self.membre} - {self.libelle} - {self.montant} FCFA"


class Parametre(models.Model):
    # ⬇️ NOUVEAU : Lien avec l'association (1 seul paramètre par asso)
    association = models.OneToOneField(
        Association, on_delete=models.CASCADE,
        related_name='parametre',
        null=True, blank=True,
        verbose_name="Association"
    )

    logo = models.ImageField(
        upload_to='logos/', blank=True, null=True,
        verbose_name="Logo de l'association"
    )
    
    nom_association = models.CharField(
        max_length=200, 
        default="ASSOCIATION DES BIOLOGISTES HAUT SASSANDRA",
        verbose_name="Nom de l'association"
    )
    
    couleur_principale = models.CharField(
        max_length=7, 
        default="#0a1c5c", 
        verbose_name="Couleur principale (format hexadécimal)",
        help_text="Ex: #0a1c5c pour du bleu marine"
    )
    
    DATE_REFERENCE_CHOICES = [
        ('date_actuelle', "Date actuelle"),
        ('derniere_reunion', "Date de la dernière réunion"),
    ]
    base_calcul_date = models.CharField(
        max_length=50,
        choices=DATE_REFERENCE_CHOICES,
        default='derniere_reunion',
        verbose_name="Base de calcul pour être à jour"
    )
    
    nombre_mois_tolerance = models.IntegerField(
        default=4,
        verbose_name="Nombre de mois de tolérance avant la date de référence",
        help_text="Un membre est à jour s'il a payé jusqu'à X mois avant la date de référence."
    )
    
    montant_cotisation_mensuelle = models.DecimalField(
        max_digits=10, decimal_places=2, default=5000,
        verbose_name="Montant de la cotisation mensuelle (FCFA)"
    )
    
    class Meta:
        verbose_name = "Paramètre"
        verbose_name_plural = "Paramètres"

    def __str__(self):
        return f"Paramètres de {self.nom_association}"


class Sauvegarde(models.Model):
    nom_fichier = models.CharField(max_length=255)
    date_creation = models.DateTimeField(auto_now_add=True)
    taille = models.IntegerField(help_text="Taille en octets")

    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Sauvegarde"
        verbose_name_plural = "Sauvegardes"

    def __str__(self):
        return self.nom_fichier