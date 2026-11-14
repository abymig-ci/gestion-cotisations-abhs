from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from cotisations.models import Association, Cotisation, Parametre
from depenses.models import Depense
from membres.models import Groupe, Membre, Poste, Reunion


class Command(BaseCommand):
    help = (
        "Rattache à une association les données qui n'en ont aucune (association vide). "
        "Sans --appliquer, affiche seulement ce qui serait changé."
    )

    def add_arguments(self, parser):
        parser.add_argument('--association', type=int, required=True, help="Numéro (id) de l'association cible")
        parser.add_argument('--appliquer', action='store_true', help="Enregistre réellement les changements")

    def handle(self, *args, **options):
        try:
            cible = Association.objects.get(pk=options['association'])
        except Association.DoesNotExist:
            raise CommandError("Cette association n'existe pas.")
        appliquer = options['appliquer']

        self.stdout.write(f"Association cible : {cible.pk} - {cible.nom}")
        self.stdout.write("MODE : " + ("APPLICATION" if appliquer else "SIMULATION (rien n'est modifié)"))

        modeles = [
            ('Membres', Membre), ('Groupes', Groupe), ('Postes', Poste), ('Réunions', Reunion),
            ('Cotisations', Cotisation), ('Dépenses', Depense), ('Paramètres', Parametre),
        ]
        for libelle, modele in modeles:
            orphelins = list(modele.objects.filter(association__isnull=True))
            self.stdout.write(f"{libelle} sans association : {len(orphelins)}")
            if not appliquer:
                continue
            ok, conflits = 0, 0
            for objet in orphelins:
                try:
                    with transaction.atomic():
                        objet.association = cible
                        objet.save(update_fields=['association'])
                    ok += 1
                except IntegrityError:
                    conflits += 1
                    self.stdout.write(self.style.WARNING(f"   conflit (doublon déjà présent dans la cible) : {objet}"))
            self.stdout.write(f"   rattachés : {ok}" + (f" | conflits : {conflits}" if conflits else ""))
