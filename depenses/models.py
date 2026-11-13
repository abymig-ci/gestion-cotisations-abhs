from django.db import models
from django.utils import timezone


class Depense(models.Model):
    CATEGORIE_CHOICES = [
        ('materiel', 'Matériel / Équipement'),
        ('transport', 'Transport / Déplacement'),
        ('evenement', 'Événement / Réunion'),
        ('soutien', 'Soutien à un membre'),
        ('autre', 'Autre'),
    ]

    # ⬇️ NOUVEAU : Lien avec l'association
    association = models.ForeignKey(
        'cotisations.Association', 
        on_delete=models.CASCADE,
        related_name='depenses',
        null=True, 
        blank=True,
        verbose_name="Association"
    )

    libelle = models.CharField(max_length=200, help_text="Ex: Achat de microscope")
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    date_depense = models.DateField(default=timezone.now)
    categorie = models.CharField(max_length=50, choices=CATEGORIE_CHOICES, default='autre')
    description = models.TextField(blank=True)
    
    # Optionnel : lier la dépense à un membre
    membre = models.ForeignKey(
        'membres.Membre', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='depenses',
        verbose_name="Membre concerné (optionnel)"
    )

    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_depense']
        verbose_name = "Dépense"
        verbose_name_plural = "Dépenses"

    def __str__(self):
        return f"{self.libelle} - {self.montant} FCFA"