from django.db import models
from django.utils import timezone

class Membre(models.Model):
    STATUT_CHOICES = [
        ('actif', 'Actif'),
        ('inactif', 'Inactif'),
        ('suspendu', 'Suspendu'),
    ]
    
    POSTE_CHOICES = [
        ('membre', 'Membre simple'),
        ('president', 'Président(e)'),
        ('vice_president', 'Vice-Président(e)'),
        ('secretaire', 'Secrétaire'),
        ('secretaire_adjoint', 'Secrétaire Adjoint(e)'),
        ('tresorier', 'Trésorier(ière)'),
        ('tresorier_adjoint', 'Trésorier(ière) Adjoint(e)'),
        ('commissaire', 'Commissaire aux comptes'),
    ]

    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    # On retire auto_now_add pour permettre la saisie manuelle
    date_adhesion = models.DateField(default=timezone.now)
    
    poste = models.CharField(
        max_length=50, 
        choices=POSTE_CHOICES, 
        default='membre',
        verbose_name="Poste dans l'association"
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