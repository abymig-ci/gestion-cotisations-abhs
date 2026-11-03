from django.db import models
from django.utils import timezone


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

    # --- NOUVELLE LOGIQUE DE STATUT DE COTISATION ---
    @property
    def statut_cotisation(self):
        aujourd_hui = timezone.now().date()
        
        # 1. Un membre inactif ou suspendu n'est pas considéré comme en retard de cotisation
        if self.statut != 'actif':
            return "Non applicable"
        
        # 2. On vérifie s'il y a des cotisations impayées dont l'échéance est dépassée
        retards = self.cotisations.filter(
            statut='en_attente', 
            date_echeance__lt=aujourd_hui
        ).count()
        
        if retards > 0:
            return "En retard"
            
        # 3. On vérifie s'il est à jour pour le mois en cours (ou s'il a payé d'avance)
        mois_actuel = aujourd_hui.month
        annee_actuelle = aujourd_hui.year
        
        # On regarde s'il y a une cotisation payée pour ce mois ou un mois futur
        est_a_jour = self.cotisations.filter(
            type_cotisation='mensuelle',
            statut='payee',
            annee__gte=annee_actuelle,
        ).filter(
            models.Q(annee__gt=annee_actuelle) | models.Q(mois__gte=mois_actuel)
        ).exists()
        
        if not est_a_jour:
            return "En retard"
            
        return "À jour"