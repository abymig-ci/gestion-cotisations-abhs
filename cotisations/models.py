from django.db import models
from django.utils import timezone
from membres.models import Membre


class Cotisation(models.Model):
    TYPE_CHOICES = [
        ('mensuelle', 'Mensuelle'),
        ('exceptionnelle', 'Exceptionnelle'),
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

    membre = models.ForeignKey(
        Membre,
        on_delete=models.CASCADE,
        related_name='cotisations'
    )
    type_cotisation = models.CharField(max_length=20, choices=TYPE_CHOICES)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    mois = models.IntegerField(choices=MOIS_CHOICES, null=True, blank=True)
    annee = models.IntegerField(default=timezone.now().year)
    date_echeance = models.DateField()
    date_paiement = models.DateField(null=True, blank=True)
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='en_attente'
    )
    libelle = models.CharField(
        max_length=200,
        blank=True,
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