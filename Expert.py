"""
Template file for expert.py module.
"""



import sys
import curses

from store import *

"""
Per realitzar l'estratègia experta s'ha de pensar què volem optimitzar.
    1. Minimitzar el moviment dels contenidors que no necessitem en cert moment
    2. Tenir a la vora els contenidors que necessitarem pròximament
Després de diverses proves i estratègies, es pot comprovar que el primer punt no aporta
tant benefici com el segon.

El funcionament de l'estratègia experta és el següent:
Emmagatzemarem els contenidors de la mateixa mida en dues piles cadascuna (com a la simple)

1. Quan arriba un contenidor nou, aquest és dipositat immediatament a la primera
pila de la seva mida.
2. A continuació, es busca quin és el primer contenidor que s'haurà d'extreure del
magatzem.
    (i) Transferim tots els contenidors que estan per sobre d'aquest a l'altra
pila de la mateixa mida.

    (ii) Quan el trobem, o bé el tractem o, si encara no el podem treure del magatzem, o bé
el separem de la resta (si sabem que sí o sí abans que se'ns acabi el temps el podrem
extreure del magatzem) o bé el deixem.

    (iii.i) Per cada mida de contenidor (és a dir, d' 1 a 4) i mentre no puguem treure el contenidor
de màxima prioritat:
        Busquem el contenidor que haurem de treure primer del magatzem i transferim
        tots els contenidors que estan per sobre d'aquest a l'altra pila de la mateixa
        mida. Aprofitem aquest temps que ens sobra perquè així quan els haguem de
        buscar més endavant ens assegurem que ho tindrem més fàcil.

    (iii.ii). Quan acabem, traiem el nostre contenidor prioritari si podem. Si no, ens esperem a què arribi el proper
contenidor sense fer res (tenim la millor disposició possible). Si el traiem, tornem al pas 2.

· Si trobem contenidors caducats, els extraiem
· Si trobem contenidors que augmenten benefici, els extraiem
· Si se'ns acaba el temps, deixem de tractar contenidors.
"""


class Strategy:

    """Implementation of the expert strategy."""

    _store: Store
    _log: Logger
    _clock: TimeStamp

    def __init__(self, width: int, log_path: str):
        if width < 20:
            raise ValueError("Not a valid width for this Expert Strategy.")

        self._store = Store(width)
        self._log = Logger(log_path, "ExpertStrategy", width)
        self._clock = 0

    def cash(self) -> int:
        """Returns amount of cash made."""

        return self._store.cash()

    def move_container(self, c: Container, new_p: Position) -> None:
        """Moves a container to a certain position."""

        self._store.move(c, new_p)
        self._log.move(self._clock, c, new_p)

    def remove_container(self, c: Container) -> None:
        """Removes a container from the Store."""

        self._store.remove(c)
        self._log.remove(self._clock, c)

    def add_container(self, c: Container, p: Position) -> None:
        """Adds a container to the Store."""

        self._store.add(c, p)
        self._log.add(self._clock, c, p)
        self._clock += 1

    def add_cash(self, c: Container) -> None:
        """Adds cash to the total amount of cash made so far."""

        self._store.add_cash(c.value)
        self._log.cash(self._clock, self.cash())

    def empty_store(self) -> bool:
        """Returns whether the store is empty or not."""

        return self._store.empty()

    def container(self, i: int) -> Container:
        """Returns the next container to be treated."""

        return self._store._containers_in_store[i]

    def treat_container(self, c: Container, new_p: Position) -> None:
        """Treats a certain container and decides whether to move it to a new position
        or remove it from the store."""

        if c.removable(self._clock):
            self.remove_container(c)
            if c.makes_profit(self._clock):
                self.add_cash(c)
        else:
            self.move_container(c, new_p)
        self._clock += 1


    def priority_list(self)-> List[Container]:
        """Returns a list with the prioritary container for each size (if not None)."""

        prioritats = [] # type: List[Container]
        for i in range(1,5):
            j = 0
            while j < self._store.size() and self.container(j).size != i:
                j += 1
            if j < self._store.size():
                insort_left(prioritats, self.container(j))
        return prioritats

    def next_comparer(self, p: Position) -> Optional[Container]:
        return self._store.top_container(p)

    def exec(self, c: Container):
        """Method that is executed every time a container arrives at the store. We
        can execute as many actions as time we have in our arrival TimeRange."""

        self._clock = c.arrival.start

        # PAS 1
        self.add_container(c, c.size * (c.size - 1))

        while self._clock < c.arrival.end and not self.empty_store():
            # PAS 2(i)
            cont = self.container(0)
            p = self._store.location(cont)[1]
            comparer = self.next_comparer(p)
            while self._clock < c.arrival.end and comparer != cont and comparer is not None:
                if p in [0, 2, 6, 12]:
                    self.treat_container(comparer, p + cont.size)
                else:
                    self.treat_container(comparer, p - cont.size)
                remaining_time -= 1
                comparer = self.next_comparer(p)

            # PAS 2(ii)
            if self._clock < c.arrival.end:
                # Pas 2(iii.i)
                if cont.delivery.start > self._clock:
                    # generem la llista amb els contenidors de major prioritat
                    prioritats = self.priority_list()
                    # per cada contenidor, executem l'estratègia exposada
                    for i in range(len(prioritats)):
                        cont_i = prioritats[i]
                        p = self._store.location(cont_i)[1]
                        comparer = self.next_comparer(p)
                        # mentre es compleixen les condicions anem tractant els contenidors de la pila del contenidor de major prioritat seleccionat
                        while self._clock < c.arrival.end and self._clock != cont.delivery.start and comparer != cont_i and comparer is not None:
                            if p in [0, 2, 6, 12]:
                                self.treat_container(comparer, p + cont_i.size)
                            else:
                                self.treat_container(comparer, p - cont_i.size)
                            comparer = self.next_comparer(p)
                    # Pas 2(iii.ii)
                    if cont.delivery.start >= self._clock and cont.delivery.start < c.arrival.end:
                        self._clock = cont.delivery.start
                        self.treat_container(cont, 20)
                    else:
                        self._clock = c.arrival.end
                else:
                    self.treat_container(cont, p)


def init_curses():
    """Initializes the curses library to get fancy colors and whatnots."""

    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    for i in range(0, curses.COLORS):
        curses.init_pair(i + 1, curses.COLOR_WHITE, i)


def execute_strategy(containers_path: str, log_path: str, width: int):
    """Execute the strategy on an empty store of a certain width reading containers from containers_path and logging to log_path."""

    containers = read_containers(containers_path)
    strategy = Strategy(width, log_path)
    for container in containers:
        strategy.exec(container)

# per executar el programa amb dades: nom de fitxer dels contenidors (probes),
# nom del fitxer on es registraran les accions i amplada del magatzem.
def main(stdscr: curses.window):
    """main script"""

    init_curses()

    containers_path = sys.argv[1]
    log_path = sys.argv[2]
    width = int(sys.argv[3])

    execute_strategy(containers_path, log_path, width)
    # podem comentar o descomentar per habilitar o deshabilitar la comprovació
    # i visualització
    check_and_show(containers_path, log_path, stdscr)


# start main script when program executed
if __name__ == '__main__':
    curses.wrapper(main)
