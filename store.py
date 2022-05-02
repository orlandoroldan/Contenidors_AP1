"""
Template file for store.py module.
"""

from dataclasses import dataclass
from typing import Optional, TextIO, List, Tuple, Dict
import curses
import time
from bisect import insort_left


# represents a moment in time.
TimeStamp = int

# left position of a container in store
Position = int

# location of container in the store, row and column (Position)
Location = Tuple[int, int]

# Time interval between two Timestamps. 'End' not included.
@dataclass
class TimeRange:
    start: TimeStamp
    end: TimeStamp

# Representa el contenidor (identificador, amplada, preu, període d'arribada
# i de lliurament)
@dataclass
class Container:
    identifier: int
    size: int
    value: int
    arrival: TimeRange
    delivery: TimeRange

    def removable(self, t: TimeStamp) -> bool:
        """Returns whether the container can be removed at a certain time."""

        return self.delivery.start <= t

    def makes_profit(self, t: TimeStamp) -> bool:
        """Assuming a container is removable, returns whether it generates profit at a certain time."""

        return self.delivery.end > t

    def __lt__(self, other) -> bool:
        """Used to compare two containers (done by delivery time)."""

        return self.delivery.start < other.delivery.start

    # We are not going to use it. But we have it in case someone wanted to check
    def valid_container(self) -> bool:
        """Used to check if a container is valid for a certain Store."""

        if self.size <= 0 or self.size > 4:
            return False
        if self.value < 0:
            return False
        if self.arrival.start > self.arrival.end:
            return False
        if self.delivery.start > self.delivery.end:
            return False
        if self.delivery.end < self.arrival.start:
            return False
        return True


# Store has no knowledge of time
class Store:

    _width: int
    _cash: int
    _frame: List[List[Container]]
    _container_location: Dict[int, Location]
    _containers_in_store: List[Container] # ordered list of containers in store, useful for expert strategies

    def __init__(self, width: int):

        if width <= 0:
            raise ValueError("The width should be a positive integer.")

        self._width = width
        self._cash = 0
        self._frame = [[] for i in range(width)]
        self._container_location = {}
        self._containers_in_store = []

    # Compl: O(1)
    def width(self) -> int:
        """Returns the width of the Store."""

        return self._width

    # Compl: O(1)
    def local_height(self, p: Position) -> int:
        """Returns the height of a certain column of the Store"""

        if p < 0 or p >= self.width():
            raise ValueError(p, "not a valid position.")

        return len(self._frame[p])

    # Compl: O(width)
    def height(self) -> int:
        """Returns the height of the Store."""

        h = 0
        for i in range(self.width()):
            h = max(self.local_height(i), h)
        return h

    # Compl: O(1)
    def size(self) -> int:
        """Returns the number of containers in the Store."""

        return len(self.containers())

    # Compl: O(1)
    def empty(self) -> bool:
        """Returns whether the Store is empty or not."""

        return  self.size() == 0

    # Compl: O(1)
    def cash(self) -> int:
        """Returns the amount of cash made."""

        return self._cash

    # Compl: O(1)
    def add_cash(self, amount: int) -> None:
        """Adds a certain amount of cash to the total cash."""

        self._cash += amount

    # Compl: O(number of containers in the store). Adding to a sorted list has running time of O(n).
    # Pre: c is a valid Container.
    def add(self, c: Container, p: Position) -> None:
        """Adds a container to a certain position."""

        if c.identifier in self._container_location.keys():
            raise AssertionError("This container is already in the Store.")

        # We could uncomment the following two lines:
        # if not c.valid_container():
        #     raise AssertionError("This is not a valid container")

        if not self.can_add(c, p):
            raise AssertionError("This Container cannot be added to this particular Position at the moment.")

        for i in range(c.size):
            self._frame[p + i].append(c)

        self._container_location[c.identifier] = (self.local_height(p) - 1, p)

        insort_left(self._containers_in_store, c)


    # Compl: O(number of containers in the store) Removing from a sorted list.
    def remove(self, c: Container) -> None:
        """Removes a container from the Store."""

        if c.identifier not in self._container_location.keys():
            raise AssertionError("This container is not in the Store.")

        if not self.can_remove(c):
            raise AssertionError("This Container cannot be removed from the Store at the moment.")

        loc = self.location(c)
        for i in range(c.size):
            self._frame[loc[1] + i].pop()

        self._containers_in_store.remove(c)

        del self._container_location[c.identifier]

    # Compl: O(number of containers in the store)
    def move(self, c: Container, p: Position) -> None:
        """Moves a container from the Store to a certain position."""

        self.remove(c)
        self.add(c, p)

    # Compl: O(1)
    def containers(self) -> List[Container]:
        """Returns a list with all the containers in the Store."""

        return self._containers_in_store

    # Compl: O(width)
    def removable_containers(self) -> List[Container]:
        """Returns a list with all the immediatly removable containers in the Store."""

        removables = [] # type: List[Container]
        for i in range(self.width()):
            top = self.top_container(i)
            if top is not None and top != removables[-1]:
                removables.append(top)
        return removables

    # Compl: O(1)
    def top_container(self, p: Position) -> Optional[Container]:
        """If not empty, returns the top container at the pth position."""

        return self._frame[p][-1] if self.local_height(p) > 0 else None

    # Compl: O(1)
    def location(self, c: Container) -> Location:
        """Returns the location of a container"""

        if c.identifier in self._container_location.keys():
            return self._container_location[c.identifier]
        raise ValueError("Container not in store. Location cannot be found.")

    # Compl: O(c.size)
    def can_add(self, c: Container, p: Position) -> bool:
        """Returns whether a container can be added in a certain position."""

        h = self.local_height(p)
        for i in range(1, c.size):
            if self.local_height(p + i) != h:
                return False
        return True

    # Compl: O(c.size)
    def can_remove(self, c: Container) -> bool:
        """Returns whether a container can be removed from the Store or not."""

        loc = self.location(c)
        for i in range(c.size):
            if self.top_container(loc[1]+i) != c:
                return False
        return True


    def write(self, stdscr: curses.window, caption: str = ''):
        maximum = 15  # maximum number of rows to write
        delay = 0.05  # delay after writing the state

        # start: clear screen
        stdscr.clear()

        # write caption
        stdscr.addstr(0, 0, caption)
        # write floor
        stdscr.addstr(maximum + 3, 0, '—' * 2 * self.width())
        # write cash
        stdscr.addstr(maximum + 4, 0, '$: ' + str(self.cash()))

        # write containers
        for c in self.containers():
            row, column = self.location(c)
            if row < maximum:
                p = 1 + c.identifier * 764351 % 250  # some random color depending on the identifier of the container
                stdscr.addstr(maximum - row + 2, 2 * column, '  ' * c.size, curses.color_pair(p))
                stdscr.addstr(maximum - row + 2, 2 * column,
                              str(c.identifier % 100), curses.color_pair(p))

        # done
        stdscr.refresh()
        time.sleep(delay)


# Registra els moviments que una estratègia realitza en un magatzem. Serveix
# per comprovar que les accions realitzades són correctes i visualitzar l'evolució
# del magatzem amb el pas del temps.
class Logger:

    """Class to log store actions to a file."""

    _file: TextIO

    def __init__(self, path: str, name: str, width: int):
        self._file = open(path, 'w')
        print(0, 'START', name, width, file=self._file)

    def add(self, t: TimeStamp, c: Container, p: Position):
        print(t, 'ADD', c.identifier, p, file=self._file)

    def remove(self, t: TimeStamp, c: Container):
        print(t, 'REMOVE', c.identifier, file=self._file)

    def move(self, t: TimeStamp, c: Container, p: Position):
        print(t, 'MOVE', c.identifier, p, file=self._file)

    def cash(self, t: TimeStamp, cash: int):
        print(t, 'CASH', cash, file=self._file)


def read_containers(path: str) -> List[Container]:
    """Returns a list of containers read from a file at path."""

    with open(path, 'r') as file:
        containers: List[Container] = []
        for line in file:
            identifier, size, value, arrival_start, arrival_end, delivery_start, delivery_end = map(
                int, line.split())
            container = Container(identifier, size, value, TimeRange(
                arrival_start, arrival_end), TimeRange(delivery_start, delivery_end))
            containers.append(container)
        return containers


def check_and_show(containers_path: str, log_path: str, stdscr: Optional[curses.window] = None):
    """
    Check that the actions stored in the log at log_path with the containers at containers_path are legal.
    Raise an exception if not.
    In the case that stdscr is not None, the store is written after each action.
    """

    # get the data
    containers_list = read_containers(containers_path)
    containers_map = {c.identifier: c for c in containers_list}
    log = open(log_path, 'r')
    lines = log.readlines()

    # process first line
    tokens = lines[0].split()
    assert len(tokens) == 4
    assert tokens[0] == "0"
    assert tokens[1] == "START"
    name = tokens[2]
    width = int(tokens[3])
    last = 0
    store = Store(width)
    if stdscr:
        store.write(stdscr)

    # process remaining lines
    for line in lines[1:]:
        tokens = line.split()
        time = int(tokens[0])
        what = tokens[1]
        assert time >= last
        last = time

        if what == "CASH":
            cash = int(tokens[2])
            assert cash == store.cash()

        elif what == "ADD":
            identifier, position = int(tokens[2]), int(tokens[3])
            store.add(containers_map[identifier], position)

        elif what == "REMOVE":
            identifier = int(tokens[2])
            container = containers_map[identifier]
            store.remove(container)
            if container.delivery.start <= time < container.delivery.end:
                store.add_cash(container.value)

        elif what == "MOVE":
            identifier, position = int(tokens[2]), int(tokens[3])
            store.move(containers_map[identifier], position)

        else:
            assert False

        if stdscr:
            store.write(stdscr, f'{name} t: {time}')
