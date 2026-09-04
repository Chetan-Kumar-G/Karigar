"""Static seed catalogue — realistic Indian artisan clusters, crafts and buyers.

Nothing here fabricates a government certificate. ``gi_status`` values mirror the
real GI register where known; anything shown to a buyer as "verified" is backed
by an explicitly-labelled *Sample Verification Record* (see ``models/passport``).
"""
from __future__ import annotations

# ── regions: (id, name, state, odop, underserved_index, lat, lon) ─────────
REGIONS = [
    ("REG-BIH-MAD", "Madhubani", "Bihar", "BIH-ODOP-MAD-PAINT", 0.82, 26.35, 86.07),
    ("REG-ASM-MAJ", "Majuli", "Assam", "ASM-ODOP-MAJ-BAMBOO", 0.88, 26.95, 94.17),
    ("REG-GUJ-KUT", "Kutch", "Gujarat", "GUJ-ODOP-KUT-EMB", 0.55, 23.73, 69.86),
    ("REG-KAR-CHN", "Channapatna", "Karnataka", "KAR-ODOP-CHN-TOYS", 0.40, 12.65, 77.21),
    ("REG-CHH-BAS", "Bastar", "Chhattisgarh", "CHH-ODOP-BAS-DHOKRA", 0.90, 19.07, 82.02),
    ("REG-RAJ-JAI", "Jaipur", "Rajasthan", "RAJ-ODOP-JAI-BLUEPOT", 0.30, 26.91, 75.79),
    ("REG-WB-NAD", "Nadia", "West Bengal", "WB-ODOP-NAD-HANDLOOM", 0.62, 23.47, 88.55),
    ("REG-OD-PUR", "Raghurajpur", "Odisha", "OD-ODOP-PUR-PATTA", 0.78, 19.90, 85.63),
    ("REG-UP-MOR", "Moradabad", "Uttar Pradesh", "UP-ODOP-MOR-BRASS", 0.45, 28.84, 78.77),
    ("REG-JK-SGR", "Srinagar", "Jammu & Kashmir", "JK-ODOP-SGR-PASHMINA", 0.68, 34.08, 74.80),
    ("REG-TN-THJ", "Thanjavur", "Tamil Nadu", "TN-ODOP-THJ-ARTPLATE", 0.58, 10.79, 79.14),
]

# ── techniques: (id, name, description, visual_keywords) ─────────────────
TECHNIQUES = [
    ("TECH-BLOCK", "hand block print", "Carved wooden blocks stamped by hand with natural dyes.", "textile,dupatta,fabric,print,cloth"),
    ("TECH-LOOM", "handloom weaving", "Yarn interlaced on a pit or frame loom without power.", "textile,saree,fabric,weave,cloth"),
    ("TECH-PAINT", "hand painting", "Fine brushwork with natural pigments on paper or cloth.", "painting,paper,canvas,art,frame"),
    ("TECH-EMB", "hand embroidery", "Needle-worked motifs, often with mirrors or zari.", "textile,fabric,embroidery,mirror,cloth"),
    ("TECH-WHEEL", "wheel throwing", "Clay shaped on a spinning wheel, then kiln-fired.", "pottery,ceramic,vase,pot,clay"),
    ("TECH-DHOKRA", "lost-wax casting", "Beeswax model encased in clay, burnt out, filled with molten brass.", "brass,metal,figurine,sculpture,bronze"),
    ("TECH-LAC", "lac turnery", "Wood turned on a lathe and coloured with lac sticks.", "wood,toy,figure,lacquer,turned"),
    ("TECH-BASKET", "hand weaving", "Split bamboo or cane coiled and woven by hand.", "basket,bamboo,cane,tray,woven"),
    ("TECH-METAL", "metal repoussé", "Sheet brass hammered from the reverse into relief.", "brass,metal,plate,engraved,utensil"),
]

# ── materials: (id, name, cost_prior_inr) ──────────────────────────────
MATERIALS = [
    ("MAT-COTTON", "cotton", 180.0), ("MAT-SILK", "silk", 650.0),
    ("MAT-WOOL", "wool", 400.0), ("MAT-BAMBOO", "bamboo", 60.0),
    ("MAT-CLAY", "clay", 40.0), ("MAT-BRASS", "brass", 520.0),
    ("MAT-WOOD", "wood", 150.0), ("MAT-PASHMINA", "pashmina wool", 2200.0),
    ("MAT-NATDYE", "natural dye", 90.0),
]

# ── crafts: (id, name, region, rarity, gi_status, gi_ref, odop, techniques, materials, heritage) ──
CRAFTS = [
    ("CRAFT-MADH", "Madhubani painting", "REG-BIH-MAD", 0.72, "registered", "GI-Application-49",
     "BIH-ODOP-MAD-PAINT", ["TECH-PAINT", "TECH-BLOCK"], ["MAT-COTTON", "MAT-NATDYE"],
     "Madhubani (Mithila) painting is a ritual wall-and-floor art of the Mithila region, "
     "traditionally made by women using fingers, twigs and natural dyes."),
    ("CRAFT-BAMB", "Assam bamboo & cane craft", "REG-ASM-MAJ", 0.6, "unregistered", None,
     "ASM-ODOP-MAJ-BAMBOO", ["TECH-BASKET"], ["MAT-BAMBOO"],
     "Bamboo and cane weaving is woven into daily life across Assam — from the japi hat "
     "to household baskets and furniture."),
    ("CRAFT-KUTCH", "Kutch mirror embroidery", "REG-GUJ-KUT", 0.65, "registered", "GI-Application-201",
     "GUJ-ODOP-KUT-EMB", ["TECH-EMB"], ["MAT-COTTON"],
     "Kutch embroidery covers many community styles (Rabari, Ahir, Mutwa), typically dense "
     "chain-stitch and abhla (mirror) work on cotton."),
    ("CRAFT-CHANNA", "Channapatna lacquerware toys", "REG-KAR-CHN", 0.5, "registered", "GI-Application-24",
     "KAR-ODOP-CHN-TOYS", ["TECH-LAC"], ["MAT-WOOD"],
     "Channapatna's 'Gombegala Ooru' (town of toys) turns ivory-wood on lathes and colours "
     "it with food-safe vegetable-lac dyes."),
    ("CRAFT-DHOKRA", "Bastar Dhokra", "REG-CHH-BAS", 0.85, "registered", "GI-Application-72",
     "CHH-ODOP-BAS-DHOKRA", ["TECH-DHOKRA"], ["MAT-BRASS"],
     "Dhokra is a 4,000-year-old lost-wax brass-casting tradition; Bastar's tribal artisans "
     "cast lamps, figurines and jewellery in a single pour."),
    ("CRAFT-BLUEPOT", "Jaipur blue pottery", "REG-RAJ-JAI", 0.55, "registered", "GI-Application-42",
     "RAJ-ODOP-JAI-BLUEPOT", ["TECH-WHEEL"], ["MAT-CLAY"],
     "Jaipur blue pottery uses no clay at all — a quartz-and-frit dough glazed in cobalt "
     "blue, a Turko-Persian technique adopted by Rajasthan."),
    ("CRAFT-HANDLOOM", "Bengal handloom cotton", "REG-WB-NAD", 0.35, "registered", "GI-Application-15",
     "WB-ODOP-NAD-HANDLOOM", ["TECH-LOOM"], ["MAT-COTTON"],
     "Phulia–Shantipur weavers produce fine handloom cotton and tangail saris on pit looms, "
     "a craft that resettled here after Partition."),
    ("CRAFT-PATTA", "Pattachitra", "REG-OD-PUR", 0.8, "registered", "GI-Application-13",
     "OD-ODOP-PUR-PATTA", ["TECH-PAINT"], ["MAT-COTTON", "MAT-NATDYE"],
     "Pattachitra ('cloth picture') from Raghurajpur uses a treated cloth-paper 'patta' and "
     "mineral colours to depict Jagannath and Krishna-lila themes."),
    ("CRAFT-BRASS", "Moradabad brass work", "REG-UP-MOR", 0.4, "registered", "GI-Application-88",
     "UP-ODOP-MOR-BRASS", ["TECH-METAL"], ["MAT-BRASS"],
     "Moradabad — 'Pital Nagri' (brass city) — has exported engraved and enamelled brassware "
     "for over 400 years."),
    ("CRAFT-PASHMINA", "Kashmir Pashmina (Kani)", "REG-JK-SGR", 0.9, "registered", "GI-Application-46",
     "JK-ODOP-SGR-PASHMINA", ["TECH-LOOM", "TECH-EMB"], ["MAT-PASHMINA"],
     "Genuine Pashmina is hand-spun from Changthangi goat down and hand-woven in Srinagar; "
     "Kani weaving builds the pattern with hundreds of wooden bobbins."),
    ("CRAFT-THANJAVUR", "Thanjavur art plate (repoussé)", "REG-TN-THJ", 0.62, "registered",
     "GI-Application-58", "TN-ODOP-THJ-ARTPLATE", ["TECH-METAL"], ["MAT-BRASS"],
     "The Thanjavur Art Plate layers hammered brass and silver repoussé over a wooden base, "
     "depicting deities and temple motifs; a registered GI of Tamil Nadu."),
]

CRAFT_RELATIONS = [
    ("CRAFT-MADH", "CRAFT-PATTA", "related", 0.8),
    ("CRAFT-PATTA", "CRAFT-MADH", "related", 0.8),
    ("CRAFT-MADH", "CRAFT-HANDLOOM", "shares_material", 0.5),
    ("CRAFT-DHOKRA", "CRAFT-BRASS", "shares_material", 0.7),
    ("CRAFT-BRASS", "CRAFT-DHOKRA", "shares_material", 0.7),
    ("CRAFT-KUTCH", "CRAFT-HANDLOOM", "shares_material", 0.5),
    ("CRAFT-CHANNA", "CRAFT-BLUEPOT", "shares_region_role", 0.4),
    ("CRAFT-PASHMINA", "CRAFT-KUTCH", "related", 0.5),
    ("CRAFT-THANJAVUR", "CRAFT-BRASS", "shares_material", 0.7),
    ("CRAFT-BRASS", "CRAFT-THANJAVUR", "shares_material", 0.7),
    ("CRAFT-THANJAVUR", "CRAFT-DHOKRA", "shares_material", 0.6),
]

# ── artisans: (id, name, phone, lang, region, craft, capacity, quality, reliability,
#               logistics_cost, verified_sales, kyc, bio) ──────────────────
ARTISANS = [
    ("ART-MEERA", "Meera Devi", "9800000001", "hi", "REG-BIH-MAD", "CRAFT-MADH",
     260, 0.74, 0.86, 4.0, 0, "verified", "First-generation Madhubani artist from Jitwarpur; "
     "learned bharni style from her mother-in-law."),
    ("ART-SUNITA", "Sunita Jha", "9800000002", "hi", "REG-BIH-MAD", "CRAFT-MADH",
     420, 0.9, 0.93, 4.5, 34, "verified", "Runs a 6-woman Madhubani collective; National Merit awardee."),
    ("ART-RupA", "Rupa Yadav", "9800000003", "hi", "REG-BIH-MAD", "CRAFT-MADH",
     180, 0.7, 0.8, 5.0, 2, "pending", "Young kachni line-work specialist."),
    ("ART-BHASKAR", "Bhaskar Hazarika", "9800000004", "as", "REG-ASM-MAJ", "CRAFT-BAMB",
     1600, 0.82, 0.88, 6.5, 12, "verified", "Third-generation bamboo weaver on Majuli island."),
    ("ART-NAYAN", "Nayan Bora", "9800000005", "as", "REG-ASM-MAJ", "CRAFT-BAMB",
     2400, 0.85, 0.9, 6.0, 41, "verified", "Supplies bamboo homeware to Guwahati exporters."),
    ("ART-DIPALI", "Dipali Saikia", "9800000006", "as", "REG-ASM-MAJ", "CRAFT-BAMB",
     1300, 0.78, 0.83, 7.0, 3, "pending", "Weaves fine japi and tokri baskets."),
    ("ART-KHIMJI", "Khimji Rabari", "9800000007", "gu", "REG-GUJ-KUT", "CRAFT-KUTCH",
     500, 0.88, 0.92, 5.5, 22, "verified", "Rabari mirror-work embroiderer near Bhuj."),
    ("ART-JAYA", "Jaya Ben", "9800000008", "gu", "REG-GUJ-KUT", "CRAFT-KUTCH",
     380, 0.8, 0.85, 5.5, 7, "verified", "Ahir-style chain stitch on yardage and cushion covers."),
    ("ART-RAGHU", "Raghu Chittara", "9800000009", "kn", "REG-KAR-CHN", "CRAFT-CHANNA",
     1200, 0.86, 0.9, 4.0, 28, "verified", "Lac-turned toys and kitchen sets; ISO food-safe dyes."),
    ("ART-LATHA", "Latha Bai", "9800000010", "kn", "REG-KAR-CHN", "CRAFT-CHANNA",
     700, 0.79, 0.82, 4.2, 4, "pending", "Educational stacking toys."),
    ("ART-BUDHRAM", "Budhram Baghel", "9800000011", "hi", "REG-CHH-BAS", "CRAFT-DHOKRA",
     220, 0.9, 0.88, 8.0, 9, "verified", "Bastar Dhokra master; Shilp Guru family."),
    ("ART-PHOOL", "Phoolo Bai", "9800000012", "hi", "REG-CHH-BAS", "CRAFT-DHOKRA",
     160, 0.83, 0.8, 8.5, 1, "pending", "Dhokra jewellery and tribal figurines."),
    ("ART-IMRAN", "Imran Khan", "9800000013", "hi", "REG-RAJ-JAI", "CRAFT-BLUEPOT",
     600, 0.84, 0.87, 4.5, 19, "verified", "Blue-pottery tiles, coasters and planters."),
    ("ART-GOPAL", "Gopal Das", "9800000014", "bn", "REG-WB-NAD", "CRAFT-HANDLOOM",
     800, 0.86, 0.91, 4.0, 37, "verified", "Phulia fine-count cotton sari weaver."),
    ("ART-ANNAPURNA", "Annapurna Maharana", "9800000015", "or", "REG-OD-PUR", "CRAFT-PATTA",
     140, 0.88, 0.85, 6.0, 6, "verified", "Raghurajpur Pattachitra; palm-leaf etching too."),
    ("ART-ARSHAD", "Arshad Bhat", "9800000016", "ur", "REG-JK-SGR", "CRAFT-PASHMINA",
     90, 0.93, 0.9, 7.5, 15, "verified", "Kani-loom Pashmina shawls, GI-tagged workshop."),

    # ── named demo cluster for the live walkthrough — Thanjavur art plates ──
    # deliberately varied capacity / quality / reliability / logistics so the
    # F6 CP-SAT split across them is visibly non-trivial.
    ("ART-CHETAN", "Chetan", "9700000001", "ta", "REG-TN-THJ", "CRAFT-THANJAVUR",
     900, 0.90, 0.93, 4.0, 24, "verified",
     "Runs a small Thanjavur art-plate workshop; fine silver repoussé, temple motifs."),
    ("ART-PRASANNAA", "Prasannaa", "9700000002", "ta", "REG-TN-THJ", "CRAFT-THANJAVUR",
     1500, 0.82, 0.86, 7.5, 11, "verified",
     "Family unit with the largest capacity in the cluster; brass-forward plates and panels."),
    ("ART-DEERAJ", "Deeraj", "9700000003", "ta", "REG-TN-THJ", "CRAFT-THANJAVUR",
     700, 0.85, 0.80, 10.0, 6, "verified",
     "Detail specialist for large 12-inch plates; lower volume, further from the hub."),
]

# ── published products: (id, artisan, craft, title, category, colors, material,
#     price, floor, rating, rating_count, quality, sales_boost_exposure) ──
PRODUCTS = [
    ("PRD-DEMO-DUP", "ART-MEERA", "CRAFT-MADH", "Madhubani hand block print cotton dupatta",
     "dupatta", ["yellow", "red"], "cotton", 649, 580, 4.5, 8, 0.74, 5, True,
     "Handwoven cotton dupatta hand block-printed with a Madhubani fish-and-lotus border."),
    ("PRD-MADH-WALL", "ART-SUNITA", "CRAFT-MADH", "Madhubani Tree of Life wall painting",
     "painting", ["black", "red", "green"], "cotton", 2400, 1600, 4.7, 41, 0.9, 260, True,
     "Bharni-style Tree of Life on handmade paper, natural dyes, 22x30 inch."),
    ("PRD-MADH-KACH", "ART-RupA", "CRAFT-MADH", "Madhubani kachni line-work greeting card set",
     "stationery", ["black", "white"], "cotton", 320, 240, 4.2, 3, 0.7, 6, True,
     "Set of 6 hand-painted kachni line-work cards."),
    ("PRD-BAMB-BASK", "ART-BHASKAR", "CRAFT-BAMB", "Assam bamboo fruit basket (round)",
     "basket", ["natural"], "bamboo", 480, 360, 4.4, 12, 0.82, 60, True,
     "Split-bamboo round fruit basket, tight coil weave, food-safe finish."),
    ("PRD-BAMB-LAMP", "ART-NAYAN", "CRAFT-BAMB", "Bamboo pendant lampshade",
     "home-decor", ["natural"], "bamboo", 890, 620, 4.6, 30, 0.85, 240, True,
     "Open-weave bamboo pendant lampshade, 30cm, E27 fitting."),
    ("PRD-BAMB-TRAY", "ART-DIPALI", "CRAFT-BAMB", "Bamboo serving tray with handles",
     "kitchen", ["natural"], "bamboo", 540, 400, 4.3, 3, 0.78, 8, True,
     "Rectangular bamboo serving tray, 40x28cm."),
    ("PRD-KUTCH-CUSH", "ART-KHIMJI", "CRAFT-KUTCH", "Kutch mirror-work cushion cover pair",
     "home-decor", ["red", "blue"], "cotton", 1300, 900, 4.6, 22, 0.88, 150, True,
     "Pair of 40cm cotton cushion covers, Rabari chain stitch and abhla mirrors."),
    ("PRD-KUTCH-YARD", "ART-JAYA", "CRAFT-KUTCH", "Ahir embroidery cotton yardage (1m)",
     "textile", ["green", "yellow"], "cotton", 950, 700, 4.4, 7, 0.8, 40, True,
     "Hand-embroidered cotton yardage, Ahir bharat, 1 metre x 44 inch."),
    ("PRD-CHANNA-STACK", "ART-RAGHU", "CRAFT-CHANNA", "Channapatna stacking ring toy",
     "toys", ["red", "yellow", "green"], "wood", 420, 300, 4.7, 28, 0.86, 130, True,
     "Lac-turned ivory-wood stacking toy, food-safe vegetable dye, 0+ years."),
    ("PRD-CHANNA-CAR", "ART-LATHA", "CRAFT-CHANNA", "Wooden push car — Channapatna lacquer",
     "toys", ["blue", "yellow"], "wood", 380, 280, 4.3, 4, 0.79, 9, True,
     "Turned-wood push car with lac finish, rounded edges."),
    ("PRD-DHOKRA-LAMP", "ART-BUDHRAM", "CRAFT-DHOKRA", "Bastar Dhokra tribal oil lamp",
     "home-decor", ["brown"], "brass", 1850, 1300, 4.8, 9, 0.9, 70, True,
     "Lost-wax cast brass diya with tribal figures, single pour, 18cm."),
    ("PRD-DHOKRA-NECK", "ART-PHOOL", "CRAFT-DHOKRA", "Dhokra brass tribal necklace",
     "jewellery", ["brown"], "brass", 1200, 850, 4.5, 1, 0.83, 6, True,
     "Hand-cast Dhokra brass necklace on adjustable cord."),
    ("PRD-BLUEPOT-SET", "ART-IMRAN", "CRAFT-BLUEPOT", "Jaipur blue pottery coaster set of 4",
     "kitchen", ["blue", "white"], "clay", 700, 500, 4.5, 19, 0.84, 90, True,
     "Quartz-body blue pottery coasters, cobalt floral, dishwasher-safe."),
    ("PRD-HANDLOOM-SAREE", "ART-GOPAL", "CRAFT-HANDLOOM", "Phulia handloom cotton saree",
     "saree", ["white", "red"], "cotton", 2600, 1900, 4.7, 37, 0.86, 220, True,
     "Fine-count Phulia handloom cotton saree with tangail-style border, 5.5m + blouse."),
    ("PRD-PATTA-JAG", "ART-ANNAPURNA", "CRAFT-PATTA", "Pattachitra Jagannath wall piece",
     "painting", ["red", "yellow", "black"], "cotton", 1600, 1150, 4.8, 6, 0.88, 45, True,
     "Natural-pigment Pattachitra on treated patta cloth, 12x16 inch, lacquer-finished."),
    ("PRD-PASH-SHAWL", "ART-ARSHAD", "CRAFT-PASHMINA", "Kani Pashmina shawl (GI-tagged workshop)",
     "shawl", ["natural", "brown"], "pashmina wool", 24000, 18000, 4.9, 15, 0.93, 110, True,
     "Hand-spun Changthangi Pashmina, Kani-woven paisley, GI-registered workshop."),

    # ── named demo cluster products (varied price ⇒ varied B2B unit cost) ──
    ("PRD-THJ-CHETAN", "ART-CHETAN", "CRAFT-THANJAVUR", "Thanjavur art plate — Lakshmi, 10 inch",
     "wall-decor", ["brown", "yellow"], "brass", 3200, 2400, 4.7, 18, 0.90, 60, True,
     "Silver-and-brass repoussé Lakshmi plate on seasoned wood, 10-inch, temple border."),
    ("PRD-THJ-PRASANNAA", "ART-PRASANNAA", "CRAFT-THANJAVUR", "Thanjavur art plate — peacock, 8 inch",
     "wall-decor", ["brown", "red"], "brass", 2600, 1950, 4.4, 12, 0.82, 30, True,
     "Brass-forward peacock plate, 8-inch, hammered relief with a beaded rim."),
    ("PRD-THJ-DEERAJ", "ART-DEERAJ", "CRAFT-THANJAVUR", "Thanjavur art plate — Krishna, 12 inch",
     "wall-decor", ["brown", "green"], "brass", 3800, 2900, 4.6, 7, 0.85, 18, True,
     "Large 12-inch Krishna plate, deep repoussé, silver highlights on a brass ground."),
]

# ── buyers: (id, name, type, phone, verified, note) ─────────────────────
BUYERS = [
    ("BUY-TAJHOTEL", "Meridian Hotels & Resorts (procurement)", "B2B", "9900000001", True,
     "Sources handmade decor and amenities for 40 properties."),
    ("BUY-GOVEMP", "State Handloom & Handicrafts Emporium", "government", "9900000002", True,
     "Government emporium chain; GeM-aligned procurement."),
    ("BUY-EXPORT", "Anokhi Exports Pvt Ltd", "B2B", "9900000003", True,
     "Exports Indian handicrafts to EU/US retail chains."),
    ("BUY-BOUTIQUE", "Terra & Weave (boutique)", "retail", "9900000004", False,
     "Single-store urban lifestyle boutique."),

    # ── named demo buyers for the live walkthrough ──
    ("BUY-AGNEAY", "Agneay Global Sourcing", "B2B", "9600000001", True,
     "Sources handmade gifting ranges for corporate and hospitality clients."),
    ("BUY-CYNTHIYA", "Cynthiya Fine Living (boutique)", "retail", "9600000002", True,
     "Curated home-decor boutique; small, frequent replenishment orders."),
    ("BUY-PRARTHANA", "Prarthana Handicrafts Trust", "government", "9600000003", True,
     "State handicrafts trust; festival-catalogue procurement, prefers verified clusters."),
]

# ── B2B requirements: (id, buyer, craft, title, material, qty, price_min, price_max,
#     days_to_deadline, fulfillment_min, is_demo, notes) ─────────────────
REQUIREMENTS = [
    ("REQ-DEMO-BASKET", "BUY-TAJHOTEL", "CRAFT-BAMB",
     "5,000 bamboo welcome baskets for hotel rooms", "bamboo",
     5000, 210, 290, 75, 1.0, True,
     "Round bamboo baskets ~25cm for in-room fruit/welcome kits across 40 properties. "
     "Consistent size, food-safe finish. Split across a cluster is acceptable."),
    ("REQ-EMP-MADH", "BUY-GOVEMP", "CRAFT-MADH",
     "800 Madhubani painted greeting-card sets for Diwali", "cotton",
     800, 260, 340, 40, 0.9, False,
     "Card sets for the emporium's festive catalogue. Prefers new/underserved artisans."),
    ("REQ-EXP-CUSH", "BUY-EXPORT", "CRAFT-KUTCH",
     "1,200 Kutch embroidery cushion covers for EU retailer", "cotton",
     1200, 700, 900, 55, 1.0, False,
     "40cm cushion covers, colour-fast, azo-free. Two design options."),

    # ── named demo cluster: bulk order that splits across Chetan/Prasannaa/Deeraj ──
    ("REQ-DEMO-THJ", "BUY-AGNEAY", "CRAFT-THANJAVUR",
     "2,900 Thanjavur art plates for a hotel-group gifting programme", "brass",
     2900, 1500, 3200, 60, 1.0, True,
     "Mixed 8–12 inch plates for a 14-hotel gifting programme. No single maker in the "
     "Thanjavur cluster can fill this alone, so a fair split across Chetan, Prasannaa and "
     "Deeraj is expected — consistency of finish matters more than one signature."),
    # ── named demo: a small order (single-artisan sized) from the boutique buyer ──
    ("REQ-DEMO-THJ-SM", "BUY-CYNTHIYA", "CRAFT-THANJAVUR",
     "60 Thanjavur art plates for a boutique launch window", "brass",
     60, 1800, 3400, 30, 1.0, True,
     "Small first order for a store launch. One maker is fine; fast turnaround preferred."),
]
