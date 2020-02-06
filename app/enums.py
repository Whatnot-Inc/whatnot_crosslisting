from enum import Enum, auto
class AutoValueEnum(Enum):
  '''Base class for states. Offers helper methods to facilitate usage'''

  def _generate_next_value_(name, start, count, last_values):
    '''Generates an auto() string value for a enum field'''
    return name.lower()

  def __str__(self):
    return str(self.value)

class MarketPlaces(AutoValueEnum):
    EBAY = auto()

class CrossListingStates(AutoValueEnum):
    CREATED = auto()
    PUBLISHING = auto()
    ACTIVE = auto()
    DISABLING = auto()
    DISABLED = auto()

class EbayOperationsStates(AutoValueEnum):
    CREATING_INVENTORY = auto()
    INVENTORY_CREATED = auto()
    CREATING_OFFER = auto()
    OFFER_CREATED = auto()
    PUBLISHING_OFFER = auto()
    OFFER_PUBLISHED = auto()
    WITHDRAWING_OFFER = auto()
    OFFER_WITHDRAWN = auto()
