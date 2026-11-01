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
    
    # Clé étrangère vers le modèle Poste
    poste = models.ForeignKey(
        Poste, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='membres',
        verbose_name="Poste dans l'association"
    )
    
    # Clé étrangère vers le modèle Groupe
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