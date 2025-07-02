# constants.py

TITLE_KEYWORD_TO_CATEGORY = {
    "storytime": "List - Storytimes",
    "math": "STEM - Math",
    "science": "STEM - Science",
    "craft": "Arts & Crafts",
    "lego": "STEM - Lego",
    "baby": "Audience - Infant", "Audience - Parent & Me",
    "toddler": "Audience - Toddler/Infant", "Audience - Parent & Me", "List - Toddler Time Events",
    "preschool": "Audience - Preschool Age", "Audience - Parent & Me",
    "steam": "List - STEM/STEAM"
    "yoga": "Category - Fitness Events"
}

LIBRARY_CONSTANTS = {
    "vbpl": {
        "program_type_to_categories": {
            "Storytimes & Early Learning": "Event Location - Virginia Beach, Audience - Free Event, Audience - Family Event, List - Storytimes",
            "STEAM": "Event Location - Virginia Beach, List - STEM/STEAM, Audience - Free Event, Audience - Family Event",
            "Computers & Technology": "Event Location - Virginia Beach, Audience - Free Event, Audience - Teens, Audience - Family Event",
            "Workshops & Lectures": "Event Location - Virginia Beach, Audience - Free Event, Audience - Family Event",
            "Discussion Groups": "Event Location - Virginia Beach, Audience - Free Event, Audience - Family Event",
            "Arts & Crafts": "Event Location - Virginia Beach, Audience - Free Event, Audience - Family Event",
            "Hobbies": "Event Location - Virginia Beach, Audience - Free Event, Audience - Family Event",
            "Books & Authors": "Event Location - Virginia Beach, Audience - Free Event, Audience - Family Event",
            "Culture": "Event Location - Virginia Beach, Audience - Free Event, Audience - Family Event",
            "History & Genealogy": "Event Location - Virginia Beach, Audience - Teens, Audience - Free Event"
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
    
    "npl": {
        "age_to_categories": {
            "Family": "Audience - Free Event, Event Location - Norfolk, Audience - Family Event",
            "All Ages": "Audience - Free Event, Event Location - Norfolk",
            "Babies (0-2)": "Audience - Free Event, Event Location - Norfolk, Audience - Parent & Me, Audience - Toddler/Infant",
            "Toddlers (2-3)": "Audience - Free Event, Event Location - Norfolk, Audience - Parent & Me, Audience - Toddler/Infant, List - Toddler Time Events",
            "Preschool (3-5)": "Audience - Free Event, Event Location - Norfolk, Audience - Parent & Me, Audience - Preschool Age",
            "Elementary School Age (5-9)": "Audience - Free Event, Event Location - Norfolk, Audience - School Age",
            "Tweens (9-13)": "Event Location - Norfolk, Audience - School Age, Audience - Free Event",
            "Teens (12-17)": "Audience - Teens, Event Location - Norfolk, Audience - Free Event, Audience - School Age"
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
            "Janaf Branch Library": "Janaf Branch Library"
        },
        "venue_names": {
            "Richard A. Tucker Memorial Library": "Richard A. Tucker Memorial Library",
            "Barron F. Black Branch Library": "Barron F. Black Branch, Norfolk Public Library",
            "Mary D. Pretlow Anchor Branch Library": "Pretlow Branch Library",
            "Jordan-Newby Anchor Branch Library at Broad Creek": "Jordan-Newby Anchor Branch Library at Broad Creek",
            "Blyden Branch Library": "Blyden Branch Library",
            "Lafayette Branch Library": "Lafayette Branch, Norfolk Public Library",
            "Larchmont Branch Library": "Larchmont Branch, Norfolk Public Library",
            "Van Wyck Branch Library": "Van Wyck Branch, Norfolk Public Library",
            "Downtown Branch at Slover": "The Slover / Downtown Branch Library",
            "Park Place Branch Library": "Park Place Branch Library",
            "Little Creek Branch Library": "Little Creek Branch, Norfolk Public Library",
            "Janaf Branch Library": "Janaf Branch Library"
        },
        "event_name_suffix": " (Norfolk)",
    },
    "chpl": {
        "age_to_categories": {
            "Preschool": "Audience - Preschool Age, Audience - Free Event, Event Location - Chesapeake, Audience - Parent & Me, Audience - Toddler/Infant, List - Toddler Time Events",
            "Elementary School": "Audience - School Age, Audience - Free Event, Event Location - Chesapeake",
            "Middle School": "Audience - Teens, Audience - Free Event, Event Location - Chesapeake",
            "High School": "Audience - Teens, Audience - Free Event, Event Location - Chesapeake",
            "Families": "Audience - Family Event, Audience - Free Event, Event Location - Chesapeake",
            "All Ages": "Audience - All Ages, Audience - Free Event, Event Location - Chesapeake",
            "Adult": "Audience - Adult Event, Audience - Free Event, Event Location - Chesapeake"
        },
        "name_suffix_map": {
            "Dr. Clarence V. Cuffee Outreach and Innovation Library": "Cuffee Library",
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
            "Major Hillard Library": "Major Hillard Library"
        },
        "event_name_suffix": " (Chesapeake)",
    },
    "hpl": {
    "program_type_to_categories": {
        "storytime": "Event Location - Hampton, Audience - Free Event, Audience - Family Event, List - Storytimes, List - Toddler Time Events",
        "lego": "Event Location - Hampton, Audience - Free Event, Audience - School Age, List - STEM/STEAM",
        "steam": "Event Location - Hampton, Audience - Free Event, Audience - School Age, List - STEM/STEAM",
        "slime": "Event Location - Hampton, Audience - Free Event, Audience - School Age, List - STEM/STEAM",
        "craft": "Event Location - Hampton, Audience - Free Event, Audience - Family Event, List - Arts & Crafts",
        "painting": "Event Location - Hampton, Audience - Free Event, Audience - Family Event, List - Arts & Crafts",
        "art": "Event Location - Hampton, Audience - Free Event, Audience - Family Event, List - Arts & Crafts",
        "baking": "Event Location - Hampton, Audience - Free Event, Audience - Family Event, List - Cooking",
        "cookie": "Event Location - Hampton, Audience - Free Event, Audience - Family Event, List - Cooking",
        "cupcake": "Event Location - Hampton, Audience - Free Event, Audience - Family Event, List - Cooking",
        "sensory": "Event Location - Hampton, Audience - Free Event, Audience - Toddler/Infant, List - Toddler Time Events",
        "chalk": "Event Location - Hampton, Audience - Free Event, Audience - Family Event, List - Outdoor Activities",
        "bubble": "Event Location - Hampton, Audience - Free Event, Audience - Family Event, List - Outdoor Activities",
        "photography": "Event Location - Hampton, Audience - Free Event, Audience - Teens, List - STEM/STEAM",
        "writing": "Event Location - Hampton, Audience - Free Event, Audience - Teens, List - Creative Writing",
        "book club": "Event Location - Hampton, Audience - Free Event, Audience - Teens, List - Reading",
        "movie": "Event Location - Hampton, Audience - Free Event, Audience - Family Event, List - Movies",
        "game": "Event Location - Hampton, Audience - Free Event, Audience - School Age, List - Games & Activities",
        "trivia": "Event Location - Hampton, Audience - Free Event, Audience - Family Event, List - Games & Activities",
        "scavenger": "Event Location - Hampton, Audience - Free Event, Audience - Family Event, List - Games & Activities",
        "hunt": "Event Location - Hampton, Audience - Free Event, Audience - Family Event, List - Games & Activities",
        "music": "Event Location - Hampton, Audience - Free Event, Audience - Family Event, List - Music & Performance",
        "dance": "Event Location - Hampton, Audience - Free Event, Audience - Family Event, List - Music & Performance",
        "teen": "Event Location - Hampton, Audience - Free Event, Audience - Teens",
        "tween": "Event Location - Hampton, Audience - Free Event, Audience - School Age"
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
        "Outside at Main Entrance": "Hampton Main Library"
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
    }
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
            "Main Street Library": "Main Street Library",
            "Grissom Library": "Grissom Library",
            "Pearl Bailey Library": "Pearl Bailey Library",
            "Avenue Branch": "Avenue Branch"
        },
        "program_type_to_categories": {
            # Tockify doesn't have program types — leave blank or extend later
        },
        "age_to_categories": {
            # Also optional unless you map ages later
        }
    }
}
