import sys
import curses

from store import *


class Strategy:

    """Implementation of the simple strategy."""

    _store: Store
    _log: Logger

    def __init__(self, width: int, log_path: str):
        if width < 20:
            raise ValueError("Not a valid width for the Simple Strategy.")

        self._store = Store(width)
        self._log = Logger(log_path, "SimpleStrategy", width)

    def cash(self) -> int:
        """Returns amount of cash made."""

        return self._store.cash()

    def move_container(self, c: Container, new_p: Position, t: TimeStamp) -> None:
        """Moves a container to a certain position."""

        self._store.move(c, new_p)
        self._log.move(t, c, new_p)


    def remove_container(self, c: Container, t: TimeStamp) -> None:
        """Removes a container from the Store."""

        self._store.remove(c)
        self._log.remove(t, c)


    def add_container(self, c: Container, p: Position, t: TimeStamp) -> None:
        """Adds a container to the Store."""

        self._store.add(c, p)
        self._log.add(t, c, p)


    def add_cash(self, c: Container, t: TimeStamp) -> None:
        """Adds cash to the total amount of cash made so far."""

        self._store.add_cash(c.value)
        self._log.cash(t, self.cash())


    def empty_store(self) -> bool:
        """Returns whether the store is empty or not."""

        return self._store.empty()

    def next_container(self, p: Position) -> Optional[Container]:
        """Returns the next container to be treated."""

        return self._store.top_container(p)

    def treat_container(self, c: Container, t: TimeStamp, new_p: Position) -> None:
        """Treats a certain container and decides whether to move it to a new position
        or remove it from the store."""

        if c.removable(t):
            self.remove_container(c, t)
            if c.makes_profit(t):
                self.add_cash(c, t)
        else:
            self.move_container(c, new_p, t)


    def exec(self, c: Container):
        """Method that is executed every time a container arrives at the store. We
        can execute as many actions as time we have in our arrival TimeRange."""

        current_time, ending_time = c.arrival.start, c.arrival.end

        self.add_container(c, c.size * (c.size - 1), current_time)
        current_time += 1

        while current_time < ending_time and not self.empty_store():
            for i in range(1, 5): # for each container size
                p, new_p = i * (i - 1), i * i
                for j in range(2): # to the right and to the left
                    cont = self.next_container(p)
                    while current_time < ending_time and cont is not None:     # cont is None when pile is empty
                        self.treat_container(cont, current_time, new_p)
                        current_time += 1
                        cont = self.next_container(p)
                    p, new_p = new_p, p


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
