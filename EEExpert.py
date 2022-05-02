import sys
import curses

from store import *

"""
El funcionament de l'estratègia experta és el següent:
Emmagatzemarem els contenidors de la mateixa mida en dues piles cadascuna (com a la simple)
Si tenim un magatzem suficientment gran, podrem implementar certes millores.

1. Quan arriba un contenidor nou, aquest és dipositat immediatament a la primera
pila de la seva mida.
2. A continuació, es busca quin és el primer contenidor que s'haurà d'extreure del
magatzem.
    (i) Transferim tots els contenidors que estan per sobre d'aquest a l'altra
pila de la mateixa mida.
    (ii) Quan el trobem, o bé el tractem o, si encara no el podem treure del magatzem el deixem on està.
    (iii.i) Per cada mida de contenidor (és a dir, d' 1 a 4) i mentre no puguem treure el contenidor
de màxima prioritat:
        Busquem el contenidor que haurem de treure primer del magatzem d'aquella mida i transferim
        tots els contenidors que estan per sobre d'aquest a l'altra pila de la mateixa
        mida
    (iii.ii). Traiem el nostre contenidor prioritari si podem. Si no, ens esperem a què arribi el proper
contenidor sense fer res. Si el traiem, tornem al pas 2.

Si volem implementar la millora per un store de 24, cada cop que trobem el contenidor
de màxima prioritat, el separarem de la resta i farem el procés (iii.i).
Si encara volem millorar més, per un magatzem de 34 agefirem 10 posicions que serviran pels contenidors
que tenen un delivery TimeRange molt curt, per així assegurar-nos que la majoria d'aquests estaran al nostre avast
quan els necessitem.

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
        if width < 34:
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

    def add_cash(self, c: Container) -> None:
        """Adds cash to the total amount of cash made so far."""

        self._store.add_cash(c.value)
        self._log.cash(self._clock, self.cash())

    def size_store(self) -> int:
        """Returns the number of containers in the store."""
        return self._store.size()

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

    def treat_add_container(self, c: Container) -> None:
        """Treats a new container and adds it to a certain Store column."""

        if c.delivery.end - c.delivery.start < 10:
            self.add_container(c, 20 + (c.size*(c.size-1) // 2))
        # amb aquesta comparació ens estalviem afegir-lo a la columna del més prioritari i fer 1 moviment inútil extra
        elif self.next_comparer(c.size *(c.size - 1)) == None or self.next_comparer(c.size * (c.size - 1)).delivery.start > c.delivery.start:
            self.add_container(c, c.size * (c.size - 1))
        else:
            self.add_container(c, c.size*c.size)
        self._clock += 1


    def priority_list(self, s: int)-> List[Container]:
        """Returns a list with the prioritary container for each size."""

        prioritats = [] #type: List[Container]
        for i in range(1,5):
            j = s
            while j < self.size_store() and self.container(j).size != i:
                j += 1
            if j < self.size_store():
                insort_left(prioritats, self.container(j))
        return prioritats

    def next_comparer(self, p: Position) -> Optional[Container]:
        """Returns the next container we will compare our prioritary container with."""

        return self._store.top_container(p)


# avís - aquesta funció està bastant malament implementada, i'm so sorry, si tingués més temps la simplificaria però ara ja em fa massa mandra
    def exec(self, c: Container):
        """Method that is executed every time a container arrives at the store. We
        can execute as many actions as time we have in our arrival TimeRange."""

        self._clock, ending_time = c.arrival.start, c.arrival.end
        self.treat_add_container(c)

        while ending_time > self._clock and not self.empty_store():

            # Pas 2(i) - tractem els contenidors de la pila del contenidor de major prioritat
            cont = self.container(0)
            p = self._store.location(cont)[1]
            comparer = self.next_comparer(p)
            while ending_time > self._clock and comparer != cont and comparer is not None:
                if p >= 20 and p < 30:
                    self.treat_container(comparer, comparer.size*comparer.size)
                elif comparer.delivery.end - comparer.delivery.start < 10:
                    self.treat_container(comparer, 20 + comparer.size*(comparer.size - 1)//2)
                else:
                    self.treat_container(comparer, p + comparer.size) if p in [0,2,6,12] else self.treat_container(comparer, p - comparer.size)
                comparer = self.next_comparer(p)

            if ending_time > self._clock:
                # Pas 2(ii) - si el podem tractar el tractem
                if cont.delivery.start <= self._clock:
                    self.treat_container(cont, p)
                else: # el movem a la columna 30 si és necessari (el voldrem tractar més endavant en el nostre interval d'arribada)
                    if cont.delivery.start < c.arrival.end:
                        self.move_container(cont, 30)
                        prioritats = self.priority_list(1)
                    else:
                        prioritats = self.priority_list(0)
                    # Pas 2(iii.i)
                    for i in range(len(prioritats)):
                        # mateixa estructura que part superior
                        cont_i = prioritats[i]
                        p = self._store.location(cont_i)[1]
                        comparer = self.next_comparer(p)
                        while ending_time > self._clock and self._clock != cont.delivery.start and comparer != cont_i and comparer is not None:
                            if p >= 20 and p < 30:
                                self.treat_container(comparer, [0,2,6,12][comparer.size - 1])
                            elif comparer.delivery.end - comparer.delivery.start < 10:
                                self.treat_container(comparer, 20 + comparer.size*(comparer.size - 1)//2)
                            else:
                                self.treat_container(comparer, p + comparer.size) if p in [0,2,6,12] else self.treat_container(comparer, p - comparer.size)
                            comparer = self.next_comparer(p)
                    # Pas 2(iii.ii)
                    if cont.delivery.start >= self._clock and cont.delivery.start < c.arrival.end:
                        self._clock = cont.delivery.start
                        self.treat_container(cont, 30)
                    else:
                        self._clock = ending_time



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
