# constants.py

TITLE_KEYWORD_TO_CATEGORY_RAW = {
    "storytime": "List - All Seasons > List - Storytimes",
    "Story Time": "List - All Seasons > List - Storytimes",
    "Storytime": "List - All Seasons > List - Storytimes",
    "baby storytime": "List - All Seasons > List - Storytimes, Audience > Audience - Toddler/Infant, Audience > Audience - Parent & Me",
    "baby Story Time": "List - All Seasons > List - Storytimes, Audience > Audience - Toddler/Infant, Audience > Audience - Parent & Me",
    "just 2s": "List - All Seasons > List - Storytimes, Audience > Audience - Toddler/Infant, Audience > Audience - Parent & Me, List - All Seasons > List - Toddler Time Events",
    "preschool": "Audience > Audience - Preschool Age",
    "babygarten": "List - All Seasons > List - Storytimes, Audience > Audience - Toddler/Infant, Audience > Audience - Parent & Me, List - All Seasons > List - Toddler Time Events",
    "babies in bloom": "List - All Seasons > List - Storytimes, Audience > Audience - Toddler/Infant, Audience > Audience - Parent & Me, List - All Seasons > List - Toddler Time Events",
    "toddler tales": "List - All Seasons > List - Storytimes",
    "teen": "Audience > Audience - Teens",
    "teens": "Audience > Audience - Teens",
    "teen time": "Audience > Audience - Teens",
    "Pre-K": "Audience > Audience - Preschool Age",
    "back to school": "List - Summer > List - Summer - Back To School",
    "Football Game": "Audience > Audience - Outdoor Event",
    "Farmer's Market": "Audience > Audience - Outdoor Event",
    "Farmers Market": "Audience > Audience - Outdoor Event",
    "Hispanic Heritage Month": "List - Fall (Category) > List - Fall - Hispanic Heritage Month (Sept/Oct)",
    "gaming": "List - All Seasons > List - Gaming Events",
    "video game": "List - All Seasons > List - Gaming Events",
    "video games": "List - All Seasons > List - Gaming Events",
    "card games": "List - All Seasons > List - Gaming Events",
    "card game": "List - All Seasons > List - Gaming Events",
    "dungeons": "List - All Seasons > List - Gaming Events, List - All Seasons > List - Cosplay Anime Comics",
    "Cubetto": "List - All Seasons > List - Gaming Events",
    "Cubetto!": "List - All Seasons > List - Gaming Events",
    "history": "List - All Seasons > List - Virginia History Events",
    "cars": "List - All Seasons > List - Car Shows & Events",
    "anime": "List - All Seasons > List - Cosplay Anime Comics",
    "manga": "List - All Seasons > List - Cosplay Anime Comics",
    "cosplay": "List - All Seasons > List - Cosplay Anime Comics",
    "comics": "List - All Seasons > List - Cosplay Anime Comics",
    "walking tour": "List - Local Tours, Audience > Audience - Outdoor Event",
    "swim": "List - All Seasons > List - Fitness & Wellness Events",
    "swimming": "List - All Seasons > List - Fitness & Wellness Events",
    "kayak": "Audience > Audience - Outdoor Event, List - All Seasons > List - Fitness & Wellness Events",
    "math": "List - All Seasons > List - STEM/STEAM",
    "science": "List - All Seasons > List - STEM/STEAM",
    "nature": "List - All Seasons > List - STEM/STEAM",
    "STEM": "List - All Seasons > List - STEM/STEAM",
    "lego": "List - All Seasons > List - STEM/STEAM",
    "chess": "List - All Seasons > List - STEM/STEAM",
    "technology": "List - All Seasons > List - STEM/STEAM",
    "stargazing": "List - Planetarium Programs & Astronomy Events",
    "fish": "List - All Seasons > List - Fishing",
    "fishing": "List - All Seasons > List - Fishing",
    "liveart": "List - All Seasons > List - Art and Crafting Events",
    "Crochet": "List - All Seasons > List - Art and Crafting Events",
    #"Terrarium": "Audience > Audience - Family Event, List - Arts & Crafts",
    "watercolor": "List - All Seasons > List - Art and Crafting Events",
    "paint": "List - All Seasons > List - Art and Crafting Events",
    "craft": "List - All Seasons > List - Art and Crafting Events",
    "crafts": "List - All Seasons > List - Art and Crafting Events",
    "crafty": "List - All Seasons > List - Art and Crafting Events",
    "art a la cart": "List - All Seasons > List - Art and Crafting Events",
    "learn to draw": "List - All Seasons > List - Art and Crafting Events",
    "learn how to draw": "List - All Seasons > List - Art and Crafting Events",
    "learning how to draw": "List - All Seasons > List - Art and Crafting Events",
    "learning to draw": "List - All Seasons > List - Art and Crafting Events",
    "baby": "Audience > Audience - Parent & Me, Audience > Audience - Toddler/Infant, List - All Seasons > List - Toddler Time Events",
    "toddler": "Audience > Audience - Toddler/Infant, Audience > Audience - Parent & Me, List - All Seasons > List - Toddler Time Events",
    "toddlers": "Audience > Audience - Toddler/Infant, Audience > Audience - Parent & Me, List - All Seasons > List - Toddler Time Events",
    "onesie":  "Audience > Audience - Toddler/Infant, Audience > Audience - Parent & Me, List - All Seasons > List - Toddler Time Events",
    "onesies": "Audience > Audience - Toddler/Infant, Audience > Audience - Parent & Me, List - All Seasons > List - Toddler Time Events",
    "preschool": "Audience > Audience - Preschool Age",
    "tiny tot": "Audience > Audience - Toddler/Infant, Audience > Audience - Parent & Me",
    "steam": "List - All Seasons > List - STEM/STEAM",
    "computers": "List - All Seasons > List - STEM/STEAM",
    "yoga": "List - All Seasons > List - Fitness & Wellness Events",
    "wellness": "List - All Seasons > List - Fitness & Wellness Events",
    "food distribution": "List - Food Distribution",
    "homeschool": "List - All Seasons > List - Homeschool",
    "KINDERSTEM": "List - All Seasons > List - STEM/STEAM, Audience > Audience - Preschool Age",
    "SPR": "Audience > Audience - Special Events, List - All Seasons > List - STEM/STEAM",
    "Build Bash": "List - All Seasons > List - STEM/STEAM",
    "austism": "Audience > Audience - Special Needs",
    "neurodiverse": "Audience > Audience - Special Needs, List - All Seasons > List - Special Needs Events",
    "neurodiversity": "Audience > Audience - Special Needs, List - All Seasons > List - Special Needs Events",
    "asd": "Audience > Audience - Special Needs, List - All Seasons > List - Special Needs Events",
    "sensory": "Audience > Audience - Special Needs, List - All Seasons > List - Special Needs Events",
    "sensory-friendly": "Audience > Audience - Special Needs, List - All Seasons > List - Special Needs Events",
    "LGBTQ+": "List - All Seasons > List - PRIDE Events",
    "Rainbow Family": "List - All Seasons > List - PRIDE Events",
    "Rainbow Families": "List - All Seasons > List - PRIDE Events",
    "theater": "Audience > Audience - Special Events",
    "Magician": "Audience > Audience - Special Events",
    "juggler": "Audience > Audience - Special Events",
    "Mom": "Audience > Audience - Parent & Me",
    "Mother": "Audience > Audience - Parent & Me",
    "Father": "Audience > Audience - Parent & Me",
    #"caregiver": "Audience > Audience - Parent & Me, Audience > Audience - Toddler/Infant",
    #"caregivers": "Audience > Audience - Parent & Me, Audience > Audience - Toddler/Infant",
    "dad": "Audience > Audience - Parent & Me",
    "weather": "Audience > Audience - Outdoor Event",
    "bird walk": "Audience > Audience - Outdoor Event", 
    "trains": "List - All Seasons > List - Events with Trains",
    "Volunteer": "List - All Seasons > List - Youth Volunteer Opportunities",
    "Volunteering": "List - All Seasons > List - Youth Volunteer Opportunities",
    "free": "Audience > Audience - Free Event",
    "all ages": "Audience > Audience - Family Event",
    "fireworks": "List - Fireworks",
    "parade": "List - All Seasons > List - Parades",
    "infant": "Audience > Audience - Toddler/Infant",
    "tween": "Audience > Audience - School Age",
    "PNO": "List - All Seasons > List - Parents Night Out",
    "taylor swift": "List - All Seasons > List - Swiftie Events",
    "Potter": "List - Wizard Events",
    "Harry Potter": "List - Wizard Events",
    "Hogwarts": "List - Wizard Events",
    "outdoor": "Audience > Audience - Outdoor Event",
    "outdoors": "Audience > Audience - Outdoor Event",
    "spooky": "List - Fall (Category) > List - Fall - Family Halloween Events",
    "halloween": "List - Fall (Category) > List - Fall - Family Halloween Events",
    "witch": "List - Fall (Category) > List - Fall - Family Halloween Events",
    "ghost": "List - Fall (Category) > List - Fall - Family Halloween Events",
    "haunted": "List - Fall (Category) > List - Fall - Family Halloween Events",
    "pumpkin": "List - Fall (Category) > List - Fall - Family Halloween Events",
    "Spooktacular": "List - Fall (Category) > List - Fall - Family Halloween Events",
    "October 31st": "List - Fall (Category) > List - Fall - Halloween Day Events",
    "Happy Halloween": "List - Fall (Category) > List - Fall - Halloween Day Events",
    "October 31": "List - Fall (Category) > List - Fall - Halloween Day Events",
    "Oct 31st": "List - Fall (Category) > List - Fall - Halloween Day Events",
    "Halloween candy": "List - Fall (Category) > List - Fall - Trick/Trunk or Treat",
    "Trick or Treat": "List - Fall (Category) > List - Fall - Trick/Trunk or Treat, List - Fall (Category) > List - Fall - Family Halloween Events",
    "Trick or Treating": "List - Fall (Category) > List - Fall - Trick/Trunk or Treat, List - Fall (Category) > List - Fall - Family Halloween Events, List - Fall (Category) > List - Fall - Halloween Day Events",
    "Trick-or-Treat": "List - Fall (Category) > List - Fall - Trick/Trunk or Treat, List - Fall (Category) > List - Fall - Family Halloween Events, List - Fall (Category) > List - Fall - Halloween Day Events",
    "trick-or-treating": "List - Fall (Category) > List - Fall - Trick/Trunk or Treat, List - Fall (Category) > List - Fall - Family Halloween Events, List - Fall (Category) > List - Fall - Halloween Day Events",
    "Trunk or Treat": "List - Fall (Category) > List - Fall - Trick/Trunk or Treat, List - Fall (Category) > List - Fall - Family Halloween Events, List - Fall (Category) > List - Fall - Halloween Day Events",
    "Trunk-or-Treat": "List - Fall (Category) > List - Fall - Trick/Trunk or Treat, List - Fall (Category) > List - Fall - Family Halloween Events, List - Fall (Category) > List - Fall - Halloween Day Events",
    "fall festival": "List - Fall (Category) > List - Fall - Fall Festivals",
    "Dia de los Muertos": "List - Fall (Category) > List - Fall - Dia de los Muertos",
    "corn maze": "List - Fall (Category) > List - Fall - Fall Festivals",
    "Diwali": "List - Fall (Category) > List - Fall - Diwali Events (November)",
    "holiday gift": "Audience > Audience - Holiday Events",
    "trim the tree": "Audience > Audience - Holiday Events",
    "trim the library tree": "Audience > Audience - Holiday Events",
    "rudolph": "Audience > Audience - Holiday Events",
    "rudolph's": "Audience > Audience - Holiday Events",
    "rudolphs": "Audience > Audience - Holiday Events",
    "ornament": "Audience > Audience - Holiday Events",
    "Ornament Workshop": "List - All Seasons > List - Art and Crafting Events",
    "snowflake": "Audience > Audience - Holiday Events",
    "Snowflakes": "Audience > Audience - Holiday Events",
    "christmas": "Audience > Audience - Holiday Events",
    "yuletide": "Audience > Audience - Holiday Events",
    "festival of lights": "Audience > Audience - Holiday Events",
    "merry market": "Audience > Audience - Holiday Events",
    "illumination": "List - Winter > List - Winter - Holiday Illumination Events, Audience > Audience - Outdoor Event, List - Winter > List - Winter - Holiday Lights",
    "christmas lights": " List - Winter > List - Winter - Holiday Illumination Events, List - Winter > List - Winter - Holiday Lights",
    "festival of lights": "Audience > Audience - Holiday Events, Audience > Audience - Outdoor Event, List - Winter > List - Winter - Holiday Lights",
    "festival of light": "Audience > Audience - Holiday Events, Audience > Audience - Outdoor Event, List - Winter > List - Winter - Holiday Lights",
    "christmas in july": "List - Summer > List - Summer - Christmas In July!",
    "santa": "List - Winter > List - Winter - Santa All",
    "grinch": "List - Winter - Grinch Events",
    "bethlehem": "List - Winter > List - Winter - Holiday Bethlehem Events",
    "Nativity": "List - Winter > List - Winter - Nativity Scenes",
    "hanukkah": "List - Winter > List - Winter - Hanukkah Events",
    "menorah": "List - Winter > List - Winter - Hanukkah Events",
    "driedel": "List - Winter > List - Winter - Hanukkah Events",
    "latke": "List - Winter > List - Winter - Hanukkah Events",
    "thanksgiving": "List - Fall (Category) > List - Fall - Thanksgiving",
    "thankful": "List - Fall (Category) > List - Fall - Thanksgiving",
    "veterans day": "List - Fall (Category) > List - Fall - Veterans Day",
    "veteran's day": "List - Fall (Category) > List - Fall - Veterans Day",
    "Native American Heritage Month": "List - Fall (Category) > List - Fall - Native American Heritage Month",
    "Arbor Day" : "List - Spring (Category) > List - Spring - Arbor Day",
    "Bike Month": "List - Spring (Category) > List - Spring - Bike Month (May)",
    "Earth Day": "List - Spring (Category) > List - Spring - Earth Day",
    "Easter" : "List - Spring (Category) > List - Spring - Easter",
    "May the Fourth": "List - Spring (Category) > List - Spring - May the Fourth Star Wars Day",
    "Memorial Day": "List - Spring (Category) > List - Spring - Memorial Day",
    "Month of the Military Child": "List - Spring (Category) > List - Spring - Month of the Military Child (April)",
    "Mothers Day": "List - Spring (Category) > List - Spring - Mothers Day",
    "Mother's Day": "List - Spring (Category) > List - Spring - Mothers Day",
    "Read Across America": "List - Spring (Category) > List - Spring - Read Across America Events (Mar 2)",
    "Spring Break": "List - Spring (Category) > List - Spring - Spring Break Events",
    "St Patricks Day": "List - Spring (Category) > List - Spring - St Patricks Day",
    "St Patrick's Day": "List - Spring (Category) > List - Spring - St Patricks Day",
    "Womens History Month": "List - Spring (Category) > List - Spring - Womens History Month (March)",
    "4th of July": "List - Summer > List - Summer - 4th of July",
    "July 4th": "List - Summer > List - Summer - 4th of July",
    "Back To School": "List - Summer > List - Summer - Back To School",
    "Fathers Day": "List - Summer > List - Summer - Fathers Day (June)",
    "Father's Day": "List - Summer > List - Summer - Fathers Day (June)",
    "Juneteenth": "List - Summer > List - Summer - Juneteenth",
    "Neighborhood Night Out": "List - Summer > List - Summer - Neighborhood Night Out (NNO) (August)",
    "Shark Week": "List - Summer > List - Summer - Shark Week (July)",
    "Black History Month": "List - Winter > List - Winter - Black History Month (February)",
    "Grinch": "List - Winter > List - Winter - Grinch Events",
    "Groundhog Day": "List - Winter > List - Winter - Groundhog Day",
    "Hanukkah Events": "List - Winter > List - Winter - Hanukkah Events",
    "Bethlehem": "List - Winter > List - Winter - Holiday Bethlehem Events",
    "Holiday Crafts": "List - Winter > List - Winter - Holiday Crafts & Gift Making",
    "Holiday Gifts": "List - Winter > List - Winter - Holiday Crafts & Gift Making",
    "Holiday Movie": "List - Winter > List - Winter - Holiday Movies",
    "Kwanzaa": "List - Winter > List - Winter - Kwanzaa Celebrations",
    "Leap Day": "List - Winter > List - Winter - Leap Day/Year Celebrations",
    "Leap Year": "List - Winter > List - Winter - Leap Day/Year Celebrations",
    "Lunar New Year": "List - Winter > List - Winter - Lunar New Year",
    "MLK Jr": "List - Winter > List - Winter - MLK Jr",
    "Martin Luther King": "List - Winter > List - Winter - MLK Jr",
    "Nativity": "List - Winter > List - Winter - Nativity Scenes",
    "New Years": "List - Winter > List - Winter - New Years Celebrations",
    "Santa": "List - Winter > List - Winter - Santa All",
    "Trees For Troops": "List - Winter > List - Winter - Trees For Troops",
    "Valentines Day": "List - Winter > List - Winter - Valentines Day",
    "Valentine's Day": "List - Winter > List - Winter - Valentines Day",
    "Valentine": "List - Winter > List - Winter - Valentines Day",
    "Winter Break": "List - Winter > List - Winter - Winter Break Events"
    
}

TITLE_KEYWORD_TO_AGE_CATEGORIES_PPL = {
    "storytime": "Audience > Audience - Preschool Age, Audience > Audience - School Age, Audience > Audience - Free Event",
    "story time": "Audience > Audience - Preschool Age, Audience > Audience - School Age, Audience > Audience - Free Event",
    "lego": "Audience > Audience - School Age, Audience > Audience - Free Event",
    "steam": "Audience > Audience - School Age, Audience > Audience - Free Event",
    "stem": "Audience > Audience - School Age, Audience > Audience - Free Event",
    "craft": "Audience > Audience - Family Event, Audience > Audience - Free Event",
    "movie": "Audience > Audience - Family Event, Audience > Audience - Free Event",
    "music": "Audience > Audience - Family Event, Audience > Audience - Free Event",
    "dance": "Audience > Audience - Family Event, Audience > Audience - Free Event",
    "sensory": "Audience > Audience - Toddler/Infant, Audience > Audience - Family Event",
    "toddlers": "Audience > Audience - Parent & Me, Audience > Audience - Toddler/Infant, List - All Seasons > List - Toddler Time Events, Audience > Audience - Free Event",
    "toddler": "Audience > Audience - Parent & Me, Audience > Audience - Toddler/Infant, List - All Seasons > List - Toddler Time Events, Audience > Audience - Free Event",
    "preschool": "Audience > Audience - Preschool Age, Audience > Audience - Free Event",
    "baby": "Audience > Audience - Parent & Me, Audience > Audience - Toddler/Infant, List - All Seasons > List - Toddler Time Events, Audience > Audience - Free Event",
}


TITLE_KEYWORD_TO_CATEGORY = {k.lower(): v for k, v in TITLE_KEYWORD_TO_CATEGORY_RAW.items()}

COMBINED_KEYWORD_TO_CATEGORY_RAW = {
    ("storytime", "toddler"): "List - All Seasons > List - Toddler Time Events, Audience > Audience - Toddler/Infant, List - All Seasons > List - Storytimes",
    ("storytime", "baby"): "Audience > Audience - Toddler/Infant, List - All Seasons > List - Storytimes",
    ("storytime", "infant"): "Audience > Audience - Toddler/Infant, List - All Seasons > List - Storytimes",
    ("story time", "toddler"): "List - All Seasons > List - Toddler Time Events, Audience > Audience - Toddler/Infant, List - All Seasons > List - Storytimes",
    ("story time", "baby"): "Audience > Audience - Toddler/Infant, List - All Seasons > List - Storytimes",
    ("story time", "infant"): "Audience > Audience - Toddler/Infant, List - All Seasons > List - Storytimes",
    ("kids", "elementary"): "Audience > Audience - School Age",
    ("kids", "grades"): "Audience > Audience - School Age"
}

COMBINED_KEYWORD_TO_CATEGORY = {
    (kw1.lower(), kw2.lower()): cat
    for (kw1, kw2), cat in COMBINED_KEYWORD_TO_CATEGORY_RAW.items()
}

UNWANTED_TITLE_KEYWORDS = [
    "summer meals",
    "Summer Meals",
    "cpr",
    "first aid",
    "3D Printer Orientation",
    "museum closed",
    "adult",
    "Community Engagement Street Team",
    "wine",
    "senior",
    "exhibit",
    "exhibition",
    "collection",
    "business",
    "lecture",
    "food drive",
    "childbirth",
    "canceled",
    "human services",
    "court mandated",
    "cancelled",
    "customer training",
    "bookmobile",
    "closed"
]

AGE_RANGE_TO_CATEGORY = [
    (0, 2, "Audience > Audience - Parent & Me, Audience > Audience - Toddler/Infant"),
    (3, 4, "Audience > Audience - Preschool Age"),
    (5, 12, "Audience > Audience - School Age"),
    (13, 17, "Audience > Audience - Teens"),
]


LIBRARY_CONSTANTS = {
    "vbpr": {
        "program_type_to_categories": {
            "Fitness & Wellness": "Event Location (Category) > Event Location - Virginia Beach, List - All Seasons > List - Fitness & Wellness Events"
        },
        "name_suffix_map": {},  # optional for location inference
        "venue_names": {
            "Kingston Elem School": "Kingston Elementary School",
            "Fairfield Elem School": "Fairfield Elementary School",
            "Williams Farm Recreation Center": "Williams Farm Recreation Center",
            "Seatack Recreation Center": "Seatack Recreation Center",
            "Bayside Recreation Center": "Bayside Recreation Center",
            "Stumpy Lake Natural Area": "Stumpy Lake Natural Area",
            "Kempsville Recreation Center": "Kempsville Recreation Center",
            "Princess Anne Recreation Center": "Princess Anne Recreation Center",
            "Great Neck Recreation Center": "Great Neck Recreation Center",
            "Bow Creek Recreation Center": "Bow Creek Recreation Center",
            "Red Wing Park": "Red Wing Park",
            "Munden Point Park": "Munden Point Park"
        },     
        "event_name_suffix": " (Virginia Beach)"
    },

    "visitchesapeake": {
        "name_suffix_map": {},
        "venue_names": {
            "Chesapeake City Park Marketplace Shelter": "Chesapeake City Park",
            "Dismal Swamp Canal Trail": "Great Dismal Swamp Canal Trail - Ches.",
            "Northwest River Park Equestrian Area": "Northwest River Park",
            "Elizabeth River Park": "Elizabeth River Boat Landing and Park",
            "Great Bridge Battlefield & Waterways Museum": "Great Bridge Battlefield and Waterways Museum",
            "Elizabeth River Park near Osprey Shelter": "Elizabeth River Boat Landing and Park",
            "Battlefield Park South": "Battlefield Park South",
            "Chesapeake Conference Center": "Chesapeake Conference Center",
            "Hickory High School": "Hickory High School",
            "Russell Memorial Library": "Russell Memorial Library",
            "Bergey's Breadbasket": "Bergey’s Breadbasket / Bergey’s Barnyard",
            "Northwest River Park & Campground": "Northwest River Park",
            "Dismal Swamp Canal Trail Head": "Great Dismal Swamp Canal Trail - Ches.",
            "Great Dismal Swamp National Wildlife Refuge - Washington Ditch Boardwalk Parking Lot": "Great Dismal Swamp Canal Trail - Ches.",
            "Great Bridge Pumpkin Patch": "Great Bridge Pumpkin Patch",
            "Greenbrier Farms": "Historic Greenbrier Farms",
            "Lilley Farms": "Lilley Farms",
            "Mount Pleasant Farms": "Mount Pleasant Farms",
            "Battlefield Park": "Battlefield Park South",
            "Big Ugly Brewing": "Big Ugly Brewing",
            "Major Hillard Library": "Major Hillard Library",
            "Great Bridge High School": "Great Bridge High School",
            "Hickory Ridge Farm": "Hickory Ridge Farm",
            "Check in at Baseball Field across street from Great Bridge Community Church": "Great Bridge Community Church",
            "Triple R Ranch": "Triple R Ranch",
            "Oak Grove Lake Park": "Oak Grove Lake Park",
            "Chesapeake Central Library": "Chesapeake Central Library",
            "Zulekia Court #35": "Zulekia Court"

            
        },
        "event_name_suffix": " (Chesapeake)"
    },
    "visithampton": {
        "name_suffix_map": {},
        "venue_names": {
            "Armstrong Stadium": "Hampton University - Armstrong Stadium",
            "The American Theater": "The American Theatre",
            "Fort Monroe Visitor & Education Center": "Fort Monroe Visitor & Education Center",
            "Ft. Monroe": "Fort Monroe Visitor & Education Center",
            "Hampton History Museum": "Hampton History Museum",
            "The Charles H. Taylor Visual Arts Center": "Charles H. Taylor Visual Arts Center",
            "Hampton Roads Convention Center": "Hampton Roads Convention Center",
            "Hampton Carousel": "Hampton Carousel",
            "Mill Point Park": "Mill Point Park",
            "Bluebird Gap Farm": "Bluebird Gap Farm",
            "St. George Brewing Company": "St. George Brewing Company",
            "Coliseum Central": "Coliseum Central",
            "Main Library": "Hampton Main Library",
            "Main Library First Floor": "Hampton Main Library",
            "Main Library Second Floor": "Hampton Main Library",
            "Main Library > Children’s Programming Room": "Hampton Main Library",
            "Willow Oaks Branch Library": "Willow Oaks Branch Library",
            "Willow Oaks Library": "Willow Oaks Branch Library",
            "Willow Oaks Branch Library Children's Area": "Willow Oaks Branch Library",
            "Willow Oaks Branch Library > Children's Area": "Willow Oaks Branch Library",
            "Northampton Branch Library": "Northampton Branch Library",
            "Northampton Library": "Northampton Branch Library",
            "Northampton": "Northampton Branch Library",
            "Phoebus Branch Library": "Phoebus Branch Library",
            "Phoebus Library": "Phoebus Branch Library",
            "Makerspace": "Hampton Main Library",
            "Children's Department": "Hampton Main Library",
            "Willow Oaks Village Square 227 Fox Hill Rd. Hampton VA 23669": "Willow Oaks Branch Library",
            "Outside library building - 4207 Victoria Blvd.  Hampton VA 23669": "Hampton Main Library",
            "Outside at Main Entrance": "Hampton Main Library",
            "Hampton Main Library": "Hamption Main Library",
            "Hampton Coliseum": "Hampton Coliseum",
            "Hampton History Museum": "Hampton History Museum",
            "The American Theatre": "The American Theatre",
            "Hampton Roads Convention Center": "Hampton Roads Convention Center",
            "Fort Monroe Visitor & Education Center": "Fort Monroe Visitor & Education Center",
            "Hampton Carousel": "Hampton Carousel",
            "Downtown Hampton": "Downtown Hampton"
        },
        "event_name_suffix": " (Hampton)"
    },
    
    "visitnewportnews": {
        "name_suffix_map": {},
        "venue_names": {
            "City Center at Oyster Point": "City Center Oyster Point",
            "Virginia Living Museum": "The Virginia Living Museum",
            "The Virginia Living Museum": "The Virginia Living Museum",
            "Lee Hall Depot": "Lee Hall Depot",
            "Historic Endview": "Endview Plantation / Historic Endview",
            "Ferguson Center for the Arts": "Ferguson Center",
            "Mary M. Torggler Fine Arts Center": "Mary M. Torggler Fine Arts Center",
            "Endview Plantation / Historic Endview": "Endview Plantation / Historic Endview",
            "Great Lawn": "Ferguson Center",
            "Tradition Brewing Company": "Tradition Brewing Company",
            "The Mariners' Museum and Park": "The Mariners’ Museum and Park",
            "Downing-Gross Cultural Arts Center": "Downing-Gross Cultural Arts Center",
            "Port Warwick": "Port Warwick",
            "Newport News Park": "Newport News Park",
            
        },
        "event_name_suffix": " (Newport News)"
    },

    "visitsuffolk": {
        "name_suffix_map": {},
        "venue_names": {
            "Embroidery &amp; Print House / Gift Shop": "Embroidery & Print House / Gift Shop",
            "Kayak Ramp at Constant's Wharf Park &amp; Marina": "Constant's Wharf",
            "Suffolk Art Gallery": "Suffolk Art Gallery",
            "Downtown Festival Park": "Downtown Festival Park",
            "Suffolk Center for Cultural Arts": "Suffolk Center for Cultural Arts",
            "Hub 757": "Hub 757",
            "Miss Lilly's Trading Post": "Miss Lilly's Trading Post",
            "Knotts Coffee Company": "Knotts Coffee Company",
            "Phillips Dawson House": "Phillips Dawson House",
            "Suffolk Family YMCA and Camp Arrowhead Conference &amp; Outdoor Center": "Suffolk Family YMCA and Camp Arrowhead Conference & Outdoor Center",
            "Riddick's Folly House Museum": "Riddicks Folly",
            "The Silos": "The Silos & Westside Burgers",
            "Constant's Wharf Park &amp; Marina": "Constant’s Wharf",
            "Constant's Wharf Park & Marina": "Constant’s Wharf",
            "Holland Ballfield": "Holland Village Ball Field 3",
            "Suffolk Executive Airport": "Suffolk Executive Airport",
            "New Realm Brewing Company - Suffolk": "New Realm Brewing Company Suffolk",
            "Sleepy Hole Park": "Sleepy Hole Park",
            "North Suffolk Library": "North Suffolk Library",
            "Lake Meade Park": "Lake Meade Park",
            "Nansemond Brewing Station": "Nansemond Brewing Station",
            "Boat Ramp at Bennett's Creek Park": "Bennett’s Creek Park",
            "Bennett's Creek Park": "Bennett's Creek Park",
            "Stillwater Tea House": "Stillwater Tea House",
            "Suffolk Visitor Center": "Suffolk Visitor’s Center",
            "Suffolk Visitor Center Pavilion": "Suffolk Visitor’s Center",
            "Sojourn Fermentory": "Sojourn Fermentory",
            "Kay's Acres": "Kay's Acres",
            "Decoys Seafood": "Decoys",
            "Maelynn Meadows": "Maelynn Meadows",
            "Downtown Suffolk": "Downtown Suffolk",
            "East Suffolk Recreation Center": "East Suffolk Recreation Center",
            "Departs from Suffolk Visitor Center": "Suffolk Visitor Center",
            "Great Dismal Swamp National Wildlife Refuge - Washington Ditch Boardwalk Parking Lot": "Great Dismal Swamp National Wildlife Refuge",
            "Chuckatuck Library": "Chuckatuck Library"
            
        },
        "event_name_suffix": " (Suffolk)"
    },

    "portsvaevents": {
        "name_suffix_map": {},
        "venue_names": {
            "Children’s Museum of Virginia": "Children's Museum of Virginia",
            "Portsmouth Naval Shipyard Museum": "Portsmouth Naval Shipyard Museum",
            "Portsmouth Art & Cultural Center": "Portsmouth Art & Cultural Center",
            "Portsmouth Colored Community Library Museum": "Portsmouth Colored Community Library Museum",
            "Portsmouth Art & Cultural Center Annex": "Portsmouth Art & Cultural Center Annex",
            "High Street Corridor": "High Street Portsmouth",
            "Atlantis Games & Comics Portsmouth": "Atlantis Games & Comics - Portsmouth",
            "Portsmouth Museums": "Children's Museum of Virginia",
            "Olde Towne Portsmouth": "Olde Towne Portsmouth",
            "Jewish Museum & Cultural Center": "Jewish Museum and Cultural Center",
            "Hoffler Creek Wildlife Preserve": "Hoffler Creek Wildlife Preserve",
            "High Street Landing": "High Street Landing",
            "4 Prints Sake": "4 Prints Sake",
            "The Hill House Museum": "Hill House Museum",
            "That Art Store": "That Art Store",
            "Paradise Creek Nature Park": "Paradise Creek Nature Park",
            "Portsmouth Welcome Center": "Portsmouth Welcome Center",
            "Afton Square": "Afton Square",
            "Commodore Theatre": "Commodore Theatre",
            "Children's Museum of Virginia": "Children’s Museum of Virginia",
            "Portsmouth Pavilion": "Portsmouth Pavilion",
            "St Johns Episcopal Church": "St. John’s Episcopal Church"
            
        },
        "event_name_suffix": " (Portsmouth)"
    },

    "visitnorfolk": {
        "name_suffix_map": {
            "Mary D. Pretlow Anchor Branch Library": "Pretlow Library",
            "Jordan-Newby Anchor Branch Library at Broad Creek": "Jordan-Newby Library",
            "Barron F. Black Branch Library": "Barron F. Black Library",
            "Richard A. Tucker Memorial Library": "Tucker Library",
            "Larchmont Branch Library": "Larchmont Library",
            "Van Wyck Branch Library": "Van Wyck Library",
            "Downtown Branch at Slover": "Slover / Downtown Library",
            "Park Place Branch Library": "Park Place Library",
            "Little Creek Branch Library": "Little Creek Library",
            "Janaf Branch Library": "Janaf Library",
            "MacArthur Memorial": "MacArthur Memorial",
            "MacArthur Center Green": "MacArthur Center Green",
            "Wells Theater": "Wells Theatre",
            "Hugh R Copeland Center": "Hugh R. Copeland Center",
            "Booker T. Washington High School": "Booker T. Washington HS",
            "Lambert's Point Community Center": "Lambert’s Point Community Center",
            "Five Points Park/Plaza": "Five Points Park/Plaza",
            "Lafayette Park": "Lafayette Park",
            "Naval Station Norfolk": "Naval Station Norfolk",
            "Virginia Zoological Park": "Virginia Zoo",
            "Starbucks at Wards Corner 7550 Granby St.  Norfolk VA 23505": "Starbucks - Wards Corner",
            "Starbucks at Wards Corner 7550 Granby St. Norfolk VA 23505": "Starbucks - Wards Corner"
        },
    
        # Raw ICS "Location" → preferred display name
        "venue_names": {
            "Richard A. Tucker Memorial Library": "Richard A. Tucker Memorial Library",
            "Barron F. Black Branch Library": "Barron F. Black Branch, Norfolk Public Library",
            "Mary D. Pretlow Anchor Branch Library": "Pretlow Branch Library",
            "Jordan-Newby Anchor Branch Library at Broad Creek": "Jordan-Newby Anchor Branch Library at Broad Creek",
            "Jordan-Newby Anchor Branch": "Jordan-Newby Anchor Branch Library at Broad Creek",
            "Blyden Branch Library": "Blyden Branch Library",
            "Lafayette Branch Library": "Lafayette Branch, Norfolk Public Library",
            "Larchmont Branch Library": "Larchmont Branch Library, Norfolk Public Library",
            "Van Wyck Branch Library": "Van Wyck Branch, Norfolk Public Library",
            "Downtown Branch at Slover": "The Slover / Downtown Branch Library",
            "Park Place Branch Library": "Park Place Branch Library",
            "Little Creek Branch Library": "Little Creek Branch, Norfolk Public Library",
            "Janaf Branch Library": "Janaf Branch, Norfolk Public Library",
            "2nd Floor Program Room": "The Slover / Downtown Branch Library",
            "2nd Floor Flex Room": "The Slover / Downtown Branch Library",
            "5th Floor Main": "The Slover / Downtown Branch Library",
            "2nd Floor Fish Bowl": "The Slover / Downtown Branch Library",
            "Collaboration Room": "Richard A. Tucker Memorial Library",
            "Larchmont@Lambert": "Lambert’s Point Recreation Center",
            "MacArthur Memorial": "MacArthur Memorial", 
            "Attucks Theatre": "Attucks Theatre",
            "Northside Park": "Northside Park",
            "Chartway Arena": "Chartway Arena",
            "MacArthur Center Green": "MacArthur Center Green",
            "Wells Theatre": "Wells Theater",
            "Hugh R Copeland Center": "Hugh R. Copeland Center",
            "Booker T. Washington High School": "Booker T. Washington High School",
            "Lambert’s Point Community Center": "Lambert’s Point Recreation Center",
            "Five Points Park/Plaza": "Five Points Park & Civic Plaza",
            "Lafayette Park": "Lafayette Park",
            "Naval Station Norfolk": "Naval Station Norfolk",
            "Virginia Zoological Park": "Virginia Zoo",
            "Hermitage Museum and Gardens": "Hermitage Museum & Gardens",
            "Starbucks at Wards Corner 7550 Granby St.  Norfolk VA 23505": "Starbucks - Wards Corner",
            "Starbucks at Wards Corner 7550 Granby St. Norfolk VA 23505": "Starbucks - Wards Corner",
            "Starbucks at Wards Corner": "Starbucks - Wards Corner",
            "Town Point Park": "Town Point Park",
            "Norview Community Center": "Norview Community Center",
            "Grandy Village": "Grandy Village Pier",
            "Harrison Opera House": "Harrison Opera House",
            "Poplar Hall Dr. at Ring Rd. (Military Circle Mall": "Military Circle Mall"
        },
    
        "program_type_to_categories": {},
    
        "age_to_categories": {
            "Infant":     "Audience > Audience - Toddler/Infant, Audience > Audience - Free Event, Event Location (Category) > Event Location - Norfolk",
            "Preschool":  "Audience > Audience - Preschool Age, Audience > Audience - Free Event, Event Location (Category) > Event Location - Norfolk",
            "School Age": "Audience > Audience - School Age, Audience > Audience - Free Event, Event Location (Category) > Event Location - Norfolk",
            "Tweens":     "Audience > Audience - School Age, Audience > Audience - Free Event, Event Location (Category) > Event Location - Norfolk",
            "Teens":      "Audience > Audience - Teens, Audience > Audience - Free Event, Event Location (Category) > Event Location - Norfolk",
            "All Ages":   "Audience > Audience - Free Event, Event Location (Category) > Event Location - Norfolk, Audience > Audience - Toddler/Infant, Audience > Audience - Preschool Age, Audience > Audience - School Age, Audience > Audience - Family Event, Audience > Audience - Teens",
            "Adults 18+": "Audience > Audience - Free Event, Event Location (Category) > Event Location - Norfolk"
        },
    
        "always_on_categories": [
            "Event Location (Category) > Event Location - Norfolk",
            "Audience > Audience - Family Event",
        ],
    
        "event_name_suffix": " (Norfolk)"
    },

    "visityorktown": {
        "name_suffix_map": {
            "Mary D. Pretlow Anchor Branch Library": "Pretlow Library",
            "Starbucks at Wards Corner 7550 Granby St. Norfolk VA 23505": "Starbucks - Wards Corner",
            "Yorktown Waterfront": "Yorktown Waterfront",
            "Riverwalk Restaurant": "Yorktown Riverwalk Landing"
        },
    
        # Raw ICS "Location" → preferred display name
        "venue_names": {
            "American Revolution Museum at Yorktown": "American Revolution Museum", 
            "Yorktown Battlefield Visitors Center": "Yorktown Battlefield Visitor Center",
            "Riverwalk Landing": "Riverwalk Landing",
            "Historic Main Street": "Historic Main Street Yorktown",
            "York Hall": "York Hall",
            "Watermen's Museum": "Watermen's Museum",
            "American Revolution Museum": "American Revolution Museum",
            "Townwide": "Yorktown, VA",
            "Yorktown Battlefield Visitor Center": "Yorktown Battlefield Visitor Center",
            "McReynolds Athletic Complex": "McReynolds Athletic Complex",
            "Grace Episcopal Church": "Grace Episcopal Church"            
        },
    
        "program_type_to_categories": {},
    
        "age_to_categories": {
            "Infant":     "Audience > Audience - Toddler/Infant, Audience > Audience - Free Event, Event Location (Category) > Event Location - Yorktown / York County",
            "Preschool":  "Audience > Audience - Preschool Age, Audience > Audience - Free Event, vent Location - Yorktown / York County",
            "School Age": "Audience > Audience - School Age, Audience > Audience - Free Event, vent Location - Yorktown / York County",
            "Tweens":     "Audience > Audience - School Age, Audience > Audience - Free Event, vent Location - Yorktown / York County",
            "Teens":      "Audience > Audience - Teens, Audience > Audience - Free Event, vent Location - Yorktown / York County",
            "All Ages":   "Audience > Audience - Free Event, vent Location - Yorktown / York County",
            "Adults 18+": "Audience > Audience - Free Event, vent Location - Yorktown / York County"
        },
    
        "always_on_categories": [
            "vent Location - Yorktown / York County",
            "Audience > Audience - Family Event",
        ],
    
        "event_name_suffix": " (Yorktown)"
    },
    
    "vbpl": {
        "program_type_to_categories": {
            "Storytimes & Early Learning": "Event Location (Category) > Event Location - Virginia Beach, Audience > Audience - Free Event, List - All Seasons > List - Storytimes",
            "STEAM": "Event Location (Category) > Event Location - Virginia Beach, List - All Seasons > List - STEM/STEAM, Audience > Audience - Free Event",
            "Computers & Technology": "Event Location (Category) > Event Location - Virginia Beach, Audience > Audience - Free Event",
            "Workshops & Lectures": "Event Location (Category) > Event Location - Virginia Beach, Audience > Audience - Free Event",
            "Discussion Groups": "Event Location (Category) > Event Location - Virginia Beach, Audience > Audience - Free Event",
            "Arts & Crafts": "Event Location (Category) > Event Location - Virginia Beach, Audience > Audience - Free Event",
            "Hobbies": "Event Location (Category) > Event Location - Virginia Beach, Audience > Audience - Free Event",
            "Books & Authors": "Event Location (Category) > Event Location - Virginia Beach, Audience > Audience - Free Event",
            "Culture": "Event Location (Category) > Event Location - Virginia Beach, Audience > Audience - Free Event",
            "History & Genealogy": "Event Location (Category) > Event Location - Virginia Beach, Audience > Audience - Free Event"
        },
        "age_to_categories": {
            # Babies / infants
            "Babies (3-12 months)": "Audience > Audience - Parent & Me, Audience > Audience - Toddler/Infant",
            "Onesies (12-24 months)": "Audience > Audience - Parent & Me, Audience > Audience - Toddler/Infant",
            "Toddlers (2-3 years)": "Audience > Audience - Parent & Me, Audience > Audience - Toddler/Infant",
        
            # Preschool
            "Preschool (3-5 years)": "Audience > Audience - Preschool Age",
        
            # Elementary
            "Grades K-2": "Audience > Audience - School Age",
            "Grades 3-5": "Audience > Audience - School Age",
        
            # Middle / High
            "Grades 6-8": "Audience > Audience - Teens",
            "Grades 9-12": "Audience > Audience - Teens",
        
            # All Ages (for Bookmobile or any VBPL “All Ages” events)
            "All Ages": "Audience > Audience - Family Event, Audience > Audience - Toddler/Infant, Audience > Audience - Preschool Age, Audience > Audience - School Age, Audience > Audience - Teens, Audience > Audience - Free Event, Event Location (Category) > Event Location - Virginia Beach"

        },
        "name_suffix_map": {
            "Oceanfront Area Library": "Oceanfront Area Library",
            "Meyera E. Oberndorf Central Library": "MEO Central Library",
            "TCC/City Joint-Use Library": "TCC Joint-Use Library",
            "Princess Anne Area Library": "Princess Anne Area Library",
            "Bayside Area Library": "Bayside Area Library",
            "Pungo-Blackwater Library": "Pungo Blackwater Library",
            "Windsor Woods Area Library": "Windsor Woods Area Library",
            "Great Neck Area Library": "Great Neck Area Library",
            "Kempsville Area Library": "Kempsville Area Library"
        },
        "venue_names": {
            "Meyera E. Oberndorf Central Library": "MEO Central Library",
            "TCC/City Joint-Use Library": "TCC Joint-Use Library",
            "Princess Anne Area Library": "Princess Anne Area Library",
            "Oceanfront Area Library": "Oceanfront Area Library",
            "Bayside Area Library": "Bayside Area Library",
            "Pungo-Blackwater Library": "Pungo Blackwater Library",
            "Windsor Woods Area Library": "Windsor Woods Area Library",
            "Great Neck Area Library": "Great Neck Area Library",
            "Kempsville Area Library": "Kempsville Area Library"
        },
            "event_name_suffix": " (Virginia Beach)"
    },

    "poquosonpl": {
        "always_on_categories": [
        "Event Location (Category) > Event Location - Poquoson",
        "Audience > Audience - Free Event",
    ],
        "program_type_to_categories": {
            "Storytimes & Early Learning": "Audience > Audience - Free Event, List - All Seasons > List - Storytimes",
            "STEAM": "List - All Seasons > List - STEM/STEAM, Audience > Audience - Free Event",
            "Computers & Technology": "Audience > Audience - Free Event",
            "Workshops & Lectures": "Audience > Audience - Free Event",
            "Discussion Groups": "Audience > Audience - Free Event",
            "Arts & Crafts": "Audience > Audience - Free Event",
            "Hobbies": "Audience > Audience - Free Event",
            "Books & Authors": "Audience > Audience - Free Event",
            "Culture": "Audience > Audience - Free Event",
            "History & Genealogy": "Audience > Audience - Freen Event"
        },
        "name_suffix_map": {
            "Great Neck Area Library": "Great Neck Area Library",
            "Kempsville Area Library": "Kempsville Area Library"
        },
        "venue_names": {
        "Great Neck Area Library": "Great Neck Area Library",
        "Kempsville Area Library": "Kempsville Area Library"
    },
        "event_name_suffix": " (Poquoson)"
    },

    "ypl": {
        "name_suffix_map": {
            "Yorktown Library": "Yorktown Library",
            "Tabb Meeting Room": "Tabb Library",
            "Tabb Library": "Tabb Library"
        },
        "venue_names": {
            "Tabb Meeting Room": "Tabb Library",
            "Yorktown Meeting Room": "Yorktown Library",
            "Yorktown Children's Wing": "Yorktown Library",
            "Tabb Program Room": "Tabb Library",
            "Tabb Fireplace": "Tabb Library",
            "Tabb Group Study Room #1": "Tabb Library",
            "Tabb Patio": "Tabb Library",
            "Tabb Youth Services": "Tabb Library",
            "Yorktown Youth Programs Room": "Yorktown Library"
        },
        "event_name_suffix": " (York County)",
        "age_to_categories": {
            "Families": "Audience > Audience - Family Event",
            #"Infants - Preschool": "Audience > Audience - Parent & Me, Audience > Audience - Toddler/Infant, List - All Seasons > List - Toddler Time Events, Audience > Audience - Preschool Age",
            "Elementary": "Audience > Audience - School Age",
            #"Children": "Audience > Audience - School Age",
            "All Ages": "Audience > Audience - Toddler/Infant, Audience > Audience - Preschool Age, Audience > Audience - School Age, Audience > Audience - Family Event",
            "Middle & High School": "Audience > Audience - Teens",
            "Adults & Teens": "Audience > Audience - Teens"
        },
    },

    "langleylibrary": {
        "name_suffix_map": {
            # "Yorktown Library": "Yorktown Library",
            # "Tabb Library": "Tabb Library"
        },
        "venue_names": {
            # "Tabb Meeting Room": "Tabb Library",
            # "Yorktown Meeting Room": "Yorktown Library",
        },
        "always_on_categories": [
            "Event Location (Category) > Event Location - Hampton",
            "Audience > Audience - Free Event",
            "Audience > Audience - Military Only"
        ],
        "event_name_suffix": " (Hampton)",
        "age_to_categories": {
        },
    },

    
    "npl": {
        "age_to_categories": {
            "Family": "Audience > Audience - Free Event, Event Location (Category) > Event Location - Norfolk, Audience > Audience - Family Event",
            "All Ages": "Audience > Audience - Free Event, Event Location (Category) > Event Location - Norfolk, Audience > Audience - Toddler/Infant, Audience > Audience - Preschool Age, Audience > Audience - School Age, Audience > Audience - Family Event", 
            "Babies (0-2)": "Audience > Audience - Free Event, Event Location (Category) > Event Location - Norfolk, Audience > Audience - Parent & Me, Audience > Audience - Toddler/Infant, List - All Seasons > List - Toddler Time Events",
            "Toddlers (2-3)": "Audience > Audience - Free Event, Event Location (Category) > Event Location - Norfolk, Audience > Audience - Toddler/Infant, List - All Seasons > List - Toddler Time Events",
            "Preschool (3-5)": "Audience > Audience - Free Event, Event Location (Category) > Event Location - Norfolk, Audience > Audience - Preschool Age",
            "Elementary School Age (5-9)": "Audience > Audience - Free Event, Event Location (Category) > Event Location - Norfolk, Audience > Audience - School Age",
            "Tweens (9-13)": "Event Location (Category) > Event Location - Norfolk, Audience > Audience - School Age, Audience > Audience - Free Event",
            "Teens (12-17)": "Audience > Audience - Teens, Event Location (Category) > Event Location - Norfolk, Audience > Audience - Free Event"
        },
        "name_suffix_map": {
            "Mary D. Pretlow Anchor Branch Library": "Pretlow Library",
            "Barron F. Black Branch Library": "Barron F. Black Library",
            "Richard A. Tucker Memorial Library": "Tucker Library",
            "Larchmont Branch Library": "Larchmont Library",
            "Jordan-Newby Anchor Branch Library at Broad Creek": "Jordan-Newby Anchor Branch Library",
            "Blyden Branch Library": "Blyden Branch Library",
            "Lafayette Branch Library": "Lafayette Branch Library",
            "Van Wyck Branch Library": "Van Wyck Branch Library",
            "Downtown Branch at Slover": "Downtown Branch at Slover",
            "Park Place Branch Library": "Park Place Branch Library",
            "Little Creek Branch Library": "Little Creek Branch Library",
            "Janaf Branch Library": "Janaf Branch Library",
            "2nd Floor Program Room": "Downtown Branch at Slover",
            "2nd Floor Flex Room": "Downtown Branch at Slover",
            "5th Floor Main": "Downtown Branch at Slover",
            "2nd Floor Fish Bowl": "Downtown Branch at Slover",
            "Collaboration Room": "Tucker Library"
        },
        "venue_names": {
            "Richard A. Tucker Memorial Library": "Richard A. Tucker Memorial Library",
            "Barron F. Black Branch Library": "Barron F. Black Branch, Norfolk Public Library",
            "Mary D. Pretlow Anchor Branch Library": "Pretlow Branch Library",
            "Jordan-Newby Anchor Branch Library at Broad Creek": "Jordan-Newby Anchor Branch Library at Broad Creek",
            "Blyden Branch Library": "Blyden Branch Library",
            "Lafayette Branch Library": "Lafayette Branch, Norfolk Public Library",
            "Larchmont Branch Library": "Larchmont Branch Library, Norfolk Public Library",
            "Van Wyck Branch Library": "Van Wyck Branch, Norfolk Public Library",
            "Downtown Branch at Slover": "The Slover / Downtown Branch Library",
            "Park Place Branch Library": "Park Place Branch Library",
            "Little Creek Branch Library": "Little Creek Branch, Norfolk Public Library",
            "Janaf Branch Library": "Janaf Branch, Norfolk Public Library",
            "2nd Floor Program Room": "The Slover / Downtown Branch Library",
            "2nd Floor Flex Room": "The Slover / Downtown Branch Library",
            "5th Floor Main": "The Slover / Downtown Branch Library",
            "2nd Floor Fish Bowl": "The Slover / Downtown Branch Library",
            "Collaboration Room": "Richard A. Tucker Memorial Library",
            "Larchmont@Lambert": "Lambert’s Point Recreation Center"
        },
        "event_name_suffix": " (Norfolk)",
    },
    "chpl": {
        "age_to_categories": {
            "Preschool": "Audience > Audience - Preschool Age, Audience > Audience - Free Event, Event Location (Category) > Event Location - Chesapeake",
            "Elementary School": "Audience > Audience - School Age, Audience > Audience - Free Event, Event Location (Category) > Event Location - Chesapeake",
            "Middle School": "Audience > Audience - Free Event, Audience > Audience - School Age, Event Location (Category) > Event Location - Chesapeake",
            "High School": "Audience > Audience - Teens, Audience > Audience - Free Event, Event Location (Category) > Event Location - Chesapeake",
            "Families": "Audience > Audience - Family Event, Audience > Audience - Free Event, Event Location (Category) > Event Location - Chesapeake",
            "All Ages": "Audience > Audience - Free Event, Event Location (Category) > Event Location - Chesapeake, Audience > Audience - Toddler/Infant, Audience > Audience - Preschool Age, Audience > Audience - School Age, Audience > Audience - Family Event, Audience > Audience - Teens",
            "Adult": "Audience > Audience - Free Event, Event Location (Category) > Event Location - Chesapeake"
        },
        "name_suffix_map": {
            "Dr. Clarence V. Cuffee Outreach and Innovation Library": "Cuffee Library",
            "Dr. Clarence V. Cuffee Library": "Cuffee Library",
            "Greenbrier Library": "Greenbrier Library",
            "Russell Memorial Library": "Russell Memorial Library",
            "Central Library": "Chesapeake Central Library",
            "Indian River Library": "Indian River Library",
            "South Norfolk Memorial Library": "South Norfolk Memorial Library",
            "Major Hillard Library": "Major Hillard Library"
        },
        "venue_names": {
            "Dr. Clarence V. Cuffee Outreach and Innovation Library": "Dr. Clarence V. Cuffee Outreach & Innovation Library",
            "Greenbrier Library": "Greenbrier Library",
            "Russell Memorial Library": "Russell Memorial Library",
            "Central Library": "Chesapeake Central Library",
            "Indian River Library": "Indian River Library",
            "South Norfolk Memorial Library": "South Norfolk Memorial Library",
            "Major Hillard Library": "Major Hillard Library",
            "Dr. Clarence V. Cuffee Library": "Dr. Clarence V. Cuffee Outreach & Innovation Library"
        },
        "always_on_categories": [
            "Event Location (Category) > Event Location - Chesapeake",
            "Audience > Audience - Free Event"
        ],
        "event_name_suffix": " (Chesapeake)"
    },
    
    "hpl": {
    "program_type_to_categories": {
        "storytime": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - Family Event, List - All Seasons > List - Storytimes, List - All Seasons > List - Toddler Time Events, Audience > Audience - Toddler/Infant",
        "lego": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - School Age, List - All Seasons > List - STEM/STEAM",
        "steam": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - School Age, List - All Seasons > List - STEM/STEAM",
        "slime": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - School Age, List - All Seasons > List - STEM/STEAM",
        "craft": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - Family Event",
        "painting": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - Family Event",
        "art": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - Family Event",
        "baking": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - Family Event, List - Cooking",
        "cookie": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - Family Event, List - Cooking",
        "cupcake": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - Family Event, List - Cooking",
        "sensory": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - Toddler/Infant, List - All Seasons > List - Toddler Time Events",
        "chalk": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - Family Event, List - Outdoor Activities",
        "bubble": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - Family Event, List - Outdoor Activities",
        "photography": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, List - All Seasons > List - STEM/STEAM",
        "writing": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, List - Creative Writing",
        "book club": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, List - Reading",
        "movie": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - Family Event, List - Movies",
        "trivia": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - Family Event",
        "scavenger": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - Family Event",
        "hunt": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - Family Event",
        "music": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - Family Event, List - Music & Performance",
        "dance": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - Family Event, List - Music & Performance",
        "teen": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - Teens",
        "tween": "Event Location (Category) > Event Location - Hampton, Audience > Audience - Free Event, Audience > Audience - School Age"
    },

    "location_map": {
        "Main Library": "Hampton Main Library",
        "Main Library First Floor": "Hampton Main Library",
        "Main Library Second Floor": "Hampton Main Library",
        "Main Library > Children’s Programming Room": "Hampton Main Library",
        "Willow Oaks Branch Library": "Willow Oaks Branch Library",
        "Willow Oaks Branch Library Children's Area": "Willow Oaks Branch Library",
        "Willow Oaks Branch Library > Children's Area": "Willow Oaks Branch Library",
        "Northampton Branch Library": "Northampton Branch Library",
        "Phoebus Branch Library": "Phoebus Branch Library",
        "Makerspace": "Hampton Main Library",
        "Children's Department": "Hampton Main Library",
        "Willow Oaks Village Square 227 Fox Hill Rd. Hampton VA 23669": "Willow Oaks Branch Library",
        "Outside library building - 4207 Victoria Blvd.  Hampton VA 23669": "Hampton Main Library",
        "Outside at Main Entrance": "Hampton Main Library",
        "1 South Mallory Street, Hampton, VA, USA": "Phoebus Branch Library",
        "227 Fox Hill Road, Hampton, VA, USA": "Willow Oaks Branch Library",
        "936 Big Bethel Road, Hampton, VA, USA": "Northampton Branch Library"
    },
    "name_suffix_map": {
        "Hampton Main Library": "Hamption Main Library",
        "Willow Oaks Branch Library": "Willow Oaks Branch Library",
        "Northampton Branch Library": "Northampton Branch Library",
        "Phoebus Branch Library": "Phoebus Branch Library"
    },
    "venue_names": {
        "Hampton Main Library": "Hamption Main Library",
        "Willow Oaks Branch Library": "Willow Oaks Branch Library",
        "Northampton Branch Library": "Northampton Branch Library",
        "Phoebus Branch Library": "Phoebus Branch Library"
    },
},
    "spl": {
        "name_suffix_map": {
            "Morgan Memorial Library": "Morgan Memorial Library",
            "North Suffolk Library": "North Suffolk Library",
            "Chuckatuck Library": "Chuckatuck Library"
        },
        "location_map": {
            "Adult Room (North Suffolk), Children's Area (North Suffolk), North Suffolk Library": "North Suffolk Library",
            "Meeting Room (Morgan Memorial), Morgan Memorial Library": "Morgan Memorial Library",
            "Morgan Memorial Library": "Morgan Memorial Library",
            "North Suffolk Library": "North Suffolk Library",
            "Chuckatuck Library": "Chuckatuck Library",
            "King's Landing Apartments: 1000 Linton Ln, Outreach": "Library2Go",
            "Constant's Wharf Park &amp; Marina": "Constant’s Wharf",
            "Constant's Wharf Park & Marina": "Constant’s Wharf",
            "Online (See Description for Details)": "Online"
        },
        "venue_names": {
            "Morgan Memorial Library": "Morgan Memorial Library",
            "North Suffolk Library": "North Suffolk Library",
            "Chuckatuck Library": "Chuckatuck Library"
        },
        "program_type_to_categories": {
            #"Early Childhood": "Audience > Audience - Family Event, Event Location (Category) > Event Location - Suffolk, Audience > Audience - Preschool Age, Audience > Audience - Free Event, Audience > Audience - Parent & Me, Audience > Audience - Toddler/Infant",
            "Elementary": "Audience > Audience - School Age, Audience > Audience - Free Event, Event Location (Category) > Event Location - Suffolk",
            "Family": "Audience > Audience - Family Event, Audience > Audience - Free Event, Event Location (Category) > Event Location - Suffolk",
            "High School": "Audience > Audience - Teens, Audience > Audience - Free Event, Event Location (Category) > Event Location - Suffolk",
            "Middle School": "Audience > Audience - Teens, Audience > Audience - Free Event, Event Location (Category) > Event Location - Suffolk",
            "All Ages": "Audience > Audience - Family Event, Audience > Audience - Free Event, Event Location (Category) > Event Location - Suffolk, Audience > Audience - Toddler/Infant, Audience > Audience - Preschool Age, Audience > Audience - School Age, Audience > Audience - Teens"
        },
        "event_name_suffix": " (Suffolk)",
        "age_to_categories": {}
    },
    "ppl": {
        "name_suffix_map": {
            "Main": "Portsmouth Main Library",
            "Main Library": "Portsmouth Main Library",
            "Churchland Branch": "Churchland Branch Library",
            "Cradock Branch": "Cradock Branch Library",
            "Manor Branch": "Manor Branch Library",
            "Coleman Meeting Room - Churchland Branch": "Churchland Branch Library",
            "Coleman Meeting Room": "Churchland Branch Library"
        },
        "venue_names": {
            "Main Library": "Portsmouth Main Library",
            "Churchland Branch": "Churchland Library",
            "Churchland Branch Library": "Churchland Library",
            "Cradock Branch": "Cradock Branch, Portsmouth Library",
            "Churchland Branch Library > Rotunda": "Churchland Library",
            "Churchland Branch Library > Children's Programming Room": "Churchland Library",
            "Children's Event Room - Main": "Portsmouth Main Library",
            "Children's Event Room": "Portsmouth Main Library",
            "Manor Library - 1401 Elmhurst Ln, Portsmouth, VA  Portsmouth VA 23704": "Manor Branch Library",
            "Manor Branch": "Manor Branch Library"
        },
        "age_to_categories": {
            "Infant": "Audience > Audience - Toddler/Infant, Audience > Audience - Free Event, Event Location (Category) > Event Location - Portsmouth",
            "Preschool": "Audience > Audience - Preschool Age, Audience > Audience - Free Event, Event Location (Category) > Event Location - Portsmouth",
            "School Age": "Audience > Audience - School Age, Audience > Audience - Free Event, Event Location (Category) > Event Location - Portsmouth",
            "Tweens": "Audience > Audience - School Age, Audience > Audience - Free Event, Event Location (Category) > Event Location - Portsmouth",
            "Teens": "Audience > Audience - Teens, Audience > Audience - Free Event, Event Location (Category) > Event Location - Portsmouth",
            "All Ages": "Audience > Audience - Free Event, Event Location (Category) > Event Location - Portsmouth, Audience > Audience - Toddler/Infant, Audience > Audience - Preschool Age, Audience > Audience - School Age, Audience > Audience - Family Event"
        },
        "program_type_to_categories": {
            # leave blank for now unless you want to map specific phrases like "STEAM", "craft", etc.
        },
        "event_name_suffix": " (Portsmouth)"
    },

    "nnpl": {
        "name_suffix_map": {
            "Main Street Library": "Main Street Library",
            "Grissom Library": "Grissom Library",
            "Pearl Bailey Library": "Pearl Bailey Library",
            "Avenue Branch": "Avenue Branch",
            "Library Branch": "Library Branch"
        },
        "venue_names": {
            "Virgil I. Grissom Library": "Grissom Library",
            "Main Street Library": "Main Street Library",
            "Pearl Bailey Library": "Pearl Bailey Library",
            "Avenue Branch": "Avenue Branch",
            "Meeting Room": "Pearl Bailey Library"  
        },
        "program_type_to_categories": {
            "Storytime": "Audience > Audience - Family Event, List - All Seasons > List - Storytimes, Event Location (Category) > Event Location - Newport News, Audience > Audience - Free Event",
            "ArtsandCrafts": "Audience > Audience - Family Event, Event Location (Category) > Event Location - Newport News, Audience > Audience - Free Event",
            "SummerReading": "Audience > Audience - Family Event, Event Location (Category) > Event Location - Newport News, Audience > Audience - Free Event",
            "Community": "Audience > Audience - Family Event, Event Location (Category) > Event Location - Newport News, Audience > Audience - Free Event",
            "Teens": "Audience > Audience - Teens, Event Location (Category) > Event Location - Newport News, Audience > Audience - Free Event",
            "Tweens": "Event Location (Category) > Event Location - Newport News, Audience > Audience - Free Event",
            "Children": "Audience > Audience - Family Event, Event Location (Category) > Event Location - Newport News, Audience > Audience - Free Event",
            "Adults": "Event Location (Category) > Event Location - Newport News, Audience > Audience - Free Event",
            "author": "List - Books & Authors, Event Location (Category) > Event Location - Newport News, Audience > Audience - Free Event",
            "STEAM": "List - All Seasons > List - STEM/STEAM, Event Location (Category) > Event Location - Newport News, Audience > Audience - Free Event",
            "Science": "List - All Seasons > List - STEM/STEAM, Event Location (Category) > Event Location - Newport News, Audience > Audience - Free Event"
        },
        "age_to_categories": {
            "Babies": "Audience > Audience - Toddler/Infant, Audience > Audience - Free Event, Event Location (Category) > Event Location - Newport News",
            "Toddlers": "Audience > Audience - Toddler/Infant, List - All Seasons > List - Toddler Time Events, Audience > Audience - Free Event, Event Location (Category) > Event Location - Newport News",
            "Preschool": "Audience > Audience - Preschool Age, Audience > Audience - Free Event, Event Location (Category) > Event Location - Newport News",
            "Children": "Audience > Audience - Family Event, Audience > Audience - Free Event, Event Location (Category) > Event Location - Newport News, Audience > Audience - School Age",
            "Kids": "Audience > Audience - Family Event, Audience > Audience - Free Event, Event Location (Category) > Event Location - Newport News",
            "Tweens": "Audience > Audience - Free Event, Event Location (Category) > Event Location - Newport News",
            "Teens": "Audience > Audience - Teens, Audience > Audience - Free Event, Event Location (Category) > Event Location - Newport News",
            "Young Adults": "Audience > Audience - Teens, Audience > Audience - Free Event, Event Location (Category) > Event Location - Newport News",
            "Adults": "Audience > Audience - Free Event, Event Location (Category) > Event Location - Newport News",
            "18+": "Audience > Audience - Free Event, Event Location (Category) > Event Location - Newport News",
            "21+": "Audience > Audience - Free Event, Event Location (Category) > Event Location - Newport News",
            "Seniors": "Audience > Audience - Seniors, Audience > Audience - Free Event, Event Location (Category) > Event Location - Newport News",
            "School Age": "Audience > Audience - Family Event, Audience > Audience - Free Event, Event Location (Category) > Event Location - Newport News, Audience > Audience - School Age",
            "All Ages": "Audience > Audience - Family Event, Audience > Audience - Free Event, Event Location (Category) > Event Location - Newport News, Audience > Audience - Toddler/Infant, Audience > Audience - Preschool Age, Audience > Audience - School Age",
            "Infant": "Audience > Audience - Toddler/Infant, Audience > Audience - Free Event, Event Location (Category) > Event Location - Newport News, Audience > Audience - Parent & Me, List - All Seasons > List - Toddler Time Events",
            "Family": "Audience > Audience - Family Event, Audience > Audience - Free Event, Event Location (Category) > Event Location - Newport News"
        }
    }
}
