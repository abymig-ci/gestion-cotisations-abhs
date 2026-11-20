from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from datetime import date
from membres.models import Membre


class Association(models.Model):
    nom = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='logos_associations/', blank=True, null=True)
    couleur_principale = models.CharField(max_length=7, default="#0a1c5c")
    est_active = models.BooleanField(default=True)
    code = models.SlugField(
        max_length=30, unique=True, null=True, blank=True,
        verbose_name="Code court",
        help_text="Abrégé en minuscules, sans espace (ex : abhs, arda). Sert au lien d'installation et au nom du raccourci : Gestcotis-abhs."
    )

    class Meta:
        verbose_name = "Association"
        verbose_name_plural = "Associations"

    def save(self, *args, **kwargs):
        # Le code est toujours enregistré en minuscules ; vide = pas de code
        self.code = (self.code or '').strip().lower() or None
        super().save(*args, **kwargs)

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

    # ⬇️ Lien avec l'association
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
    # ⬇️ Lien avec l'association (1 seul paramètre par asso)
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
    
    # ⬇️ NOUVEAU CHAMP : Stockage permanent du logo en texte (Base64)
    logo_base64 = models.TextField(
        blank=True, 
        null=True, 
        help_text="Stockage permanent du logo pour Render (base64)"
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
    mois_carence = models.PositiveSmallIntegerField(
        default=6,
        verbose_name="Mois de carence des nouveaux membres",
        help_text="Durée pendant laquelle un nouveau membre est « en carence » après son adhésion (0 = pas de carence)."
    )
    
    montant_cotisation_mensuelle = models.DecimalField(
        max_digits=10, decimal_places=2, default=5000,
        verbose_name="Montant de la cotisation mensuelle (FCFA)"
    )
    
    messages_defilants = models.TextField(
        blank=True, default='',
        verbose_name="Messages défilants (Mon espace)",
        help_text="Un message par ligne. Ils défilent en boucle sur la page « Mon espace » des membres."
    )

    # --- Montants de départ (association existant depuis longtemps) ---
    montants_initiaux_actifs = models.BooleanField(
        default=False,
        verbose_name="Activer les montants de départ",
        help_text="Réservé au super utilisateur. Une fois activé, les autres utilisateurs ayant accès aux paramètres voient et peuvent remplir les deux montants ci-dessous."
    )
    depenses_initiales = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Total des dépenses de départ (FCFA)",
        help_text="Dépenses déjà effectuées avant l'utilisation de l'application."
    )
    solde_initial = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Solde en caisse de départ (FCFA)",
        help_text="Montant en caisse avant l'utilisation de l'application."
    )

    class Meta:
        verbose_name = "Paramètre"
        verbose_name_plural = "Paramètres"

    def liste_messages(self):
        return [ligne.strip() for ligne in (self.messages_defilants or '').splitlines() if ligne.strip()]

    def __str__(self):
        return f"Paramètres de {self.nom_association}"


class CotisationLibre(models.Model):
    """Collecte libre (dons des membres) : indépendante des autres cotisations, hors comptabilité."""
    association = models.ForeignKey(
        Association, on_delete=models.CASCADE,
        related_name='cotisations_libres',
        null=True, blank=True,
        verbose_name="Association"
    )
    motif = models.CharField(max_length=200, verbose_name="Motif de la cotisation")
    date_cotisation = models.DateField(default=date.today, verbose_name="Date")
    description = models.TextField(blank=True, verbose_name="Description")
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_cotisation', '-id']
        verbose_name = "Cotisation libre"
        verbose_name_plural = "Cotisations libres"

    def total(self):
        return self.dons.aggregate(total=Sum('montant'))['total'] or 0

    def __str__(self):
        return self.motif


class DonCotisationLibre(models.Model):
    """Don d'un membre dans une cotisation libre."""
    cotisation = models.ForeignKey(
        CotisationLibre, on_delete=models.CASCADE, related_name='dons'
    )
    membre = models.ForeignKey(
        Membre, on_delete=models.CASCADE, related_name='dons_libres'
    )
    montant = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = [('cotisation', 'membre')]
        verbose_name = "Don (cotisation libre)"
        verbose_name_plural = "Dons (cotisations libres)"

    def __str__(self):
        return f"{self.membre} - {self.montant} FCFA"


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


class EmpreinteAppareil(models.Model):
    """Appareil enregistré par un utilisateur pour se connecter par empreinte digitale (WebAuthn).
    Seule la clé publique est stockée : l'empreinte elle-même reste dans le téléphone."""
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='empreintes'
    )
    credential_id = models.CharField(max_length=512, unique=True)
    cle_publique = models.TextField()
    compteur = models.PositiveBigIntegerField(default=0)
    nom = models.CharField(max_length=100, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    derniere_utilisation = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Empreinte (appareil)"
        verbose_name_plural = "Empreintes (appareils)"

    def __str__(self):
        return f"{self.utilisateur} - {self.nom or 'appareil'}"
