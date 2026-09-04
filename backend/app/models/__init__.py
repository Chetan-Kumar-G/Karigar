"""Import every model so ``Base.metadata`` is complete before ``create_all``."""
from app.db.base import Base
from app.models.artisan_product import (
    Artisan,
    Inventory,
    Product,
    ProductAttribute,
    ProductImage,
)
from app.models.commerce import Buyer, BuyerRequirement, Order, OrderAllocation
from app.models.geo_craft import (
    Cluster,
    Craft,
    CraftRelation,
    Material,
    Region,
    Technique,
    craft_material,
    craft_technique,
)
from app.models.market import (
    DemandForecast,
    DemandSignal,
    MarketPrice,
    PriceHistory,
)
from app.models.marketplace import AiRun, Exposure, Interaction, Listing
from app.models.passport import Certification, CraftPassport
from app.models.trust import (
    B2BOrderCommitment,
    Complaint,
    TrustEvent,
    VerificationEvidence,
    VerificationProfile,
    VerificationReview,
)

__all__ = [
    "Base",
    "Region", "Cluster", "Craft", "Technique", "Material", "CraftRelation",
    "craft_material", "craft_technique",
    "Artisan", "Product", "ProductImage", "ProductAttribute", "Inventory",
    "CraftPassport", "Certification",
    "Buyer", "BuyerRequirement", "Order", "OrderAllocation",
    "PriceHistory", "MarketPrice", "DemandSignal", "DemandForecast",
    "Listing", "Exposure", "Interaction", "AiRun",
    "VerificationProfile", "VerificationEvidence", "VerificationReview",
    "Complaint", "TrustEvent", "B2BOrderCommitment",
]
