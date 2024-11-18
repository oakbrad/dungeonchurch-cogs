"""
THE ORACLE for the THE QUIET YEAR
https://buriedwithoutceremony.com/the-quiet-year

All text in this file is by Alder Avery of Buried Ceremony

Converted from:
https://buriedwithoutceremony.com/wp-content/uploads/2019/08/The-Quiet-Year-Oracle.pdf

"""

oracle = {
    "Hearts": {  # Spring
        "A": {
            "prompt": None,
            "options": [
                {
                    "text": "What group has the highest status in the community? What must people do to gain inclusion in this group?",
                    "mechanics": []
                },
                {
                    "text": "Are there distinct family units in the community? If so, what family structures are common?",
                    "mechanics": []
                }
            ]
        },
        "2": {
            "prompt": None,
            "options": [
                {
                    "text": "There's a large body of water on the map. Where is it? What does it look like?",
                    "mechanics": []
                },
                {
                    "text": "There's a giant man-made structure on the map. Where is it? Why is it abandoned?",
                    "mechanics": []
                }
            ]
        },
        "3": {
            "prompt": None,
            "options": [
                {
                    "text": "Someone new arrives. Who?",
                    "mechanics": []
                },
                {
                    "text": "Two of the community's younger members get into a fight. What provoked them?",
                    "mechanics": []
                }
            ]
        },
        "4": {
            "prompt": None,
            "options": [
                {
                    "text": "What important and basic tools does the community lack?",
                    "mechanics": []
                },
                {
                    "text": "Where are you storing your food? Why is this a risky place to store things?",
                    "mechanics": []
                }
            ]
        },
        "5": {
            "prompt": None,
            "options": [
                {
                    "text": "There is a disquieting legend about this place. What is it?",
                    "mechanics": []
                },
                {
                    "text": "Alarming weather patterns destroy something. How and what?",
                    "mechanics": []
                }
            ]
        },
        "6": {
            "prompt": None,
            "options": [
                {
                    "text": "Are there children in the community? If there are, what is their role in the community?",
                    "mechanics": []
                },
                {
                    "text": "How old are the eldest members of the community? What unique needs do they have?",
                    "mechanics": []
                }
            ]
        },
        "7": {
            "prompt": None,
            "options": [
                {
                    "text": "Where does everyone sleep? Who is unhappy with this arrangement, and why?",
                    "mechanics": []
                },
                {
                    "text": "What natural predators roam this area? Are you safe?",
                    "mechanics": []
                }
            ]
        },
        "8": {
            "prompt": None,
            "options": [
                {
                    "text": "An old piece of machinery is discovered, broken but perhaps repairable. What is it? What would it be useful for?",
                    "mechanics": []
                },
                {
                    "text": "An old piece of machinery is discovered, cursed and dangerous. How does the community destroy it?",
                    "mechanics": []
                }
            ]
        },
        "9": {
            "prompt": None,
            "options": [
                {
                    "text": "A charismatic young girl convinces many to help her with an elaborate scheme. What is it? Who joins her endeavors?",
                    "mechanics": [
                        {
                            "type": "start_project",
                            "effect": "Reflect the scheme as a project."
                        }
                    ]
                },
                {
                    "text": "A charismatic young girl tries to tempt many into sinful or dangerous activity. Why does she do this? How does the community respond?",
                    "mechanics": []
                }
            ]
        },
        "10": {
            "prompt": None,
            "options": [
                {
                    "text": "There's another community somewhere on the map. Where are they? What sets them apart from you?",
                    "mechanics": []
                },
                {
                    "text": "What belief or practice helps to unify your community?",
                    "mechanics": []
                }
            ]
        },
        "J": {
            "prompt": None,
            "options": [
                {
                    "text": "You see a good omen. What is it?",
                    "mechanics": []
                },
                {
                    "text": "You see a bad omen. What is it?",
                    "mechanics": []
                }
            ]
        },
        "Q": {
            "prompt": None,
            "options": [
                {
                    "text": "What's the most beautiful thing in this area?",
                    "mechanics": []
                },
                {
                    "text": "What's the most hideous thing in this area?",
                    "mechanics": []
                }
            ]
        },
        "K": {
            "prompt": None,
            "options": [
                {
                    "text": "A young boy starts digging in the ground, and discovers something unexpected. What is it?",
                    "mechanics": []
                },
                {
                    "text": "An old man confesses to past crimes and atrocities. What has he done?",
                    "mechanics": []
                }
            ]
        }
    },

    "Diamonds": {  # Summer
        "A": {
            "prompt": None,
            "options": [
                {
                    "text": "A contingent within the community demand to be heard. Who are they? What are they asking for?",
                    "mechanics": []
                },
                {
                    "text": "A contingent within the community have acted on their frustrations. What have they damaged, and why did they damage it? Is it permanent?",
                    "mechanics": []
                }
            ]
        },
        "2": {
            "prompt": None,
            "options": [
                {
                    "text": "Someone new arrives. Who? Why are they in distress?",
                    "mechanics": []
                },
                {
                    "text": "Someone leaves the community. Who? What are they looking for?",
                    "mechanics": []
                }
            ]
        },
        "3": {
            "prompt": None,
            "options": [
                {
                    "text": "Summer is a time for production and tending to the earth.",
                    "mechanics": [
                        {
                            "type": "start_project",
                            "effect": "Start a project related to food production."
                        }
                    ]
                },
                {
                    "text": "Summer is a time for conquest and the gathering of might.",
                    "mechanics": [
                        {
                            "type": "start_project",
                            "effect": "Start a project related to military readiness and conquest."
                        }
                    ]
                }
            ]
        },
        "4": {
            "prompt": None,
            "options": [
                {
                    "text": "The eldest among you dies. What caused the death?",
                    "mechanics": []
                },
                {
                    "text": "The eldest among you is very sick. Caring for them and searching for a cure requires the help of the entire community.",
                    "mechanics": [
                        {
                            "type": "turn_effect",
                            "effect": "Do not reduce project dice this week."
                        }
                    ]
                }
            ]
        },
        "5": {
            "prompt": None,
            "options": [
                {
                    "text": "A project finishes early. What led to its early completion?",
                    "mechanics": [
                        {
                            "type": "project_management",
                            "effect": "Finish a project early."
                        }
                    ]
                },
                {
                    "text": "The weather is nice and people can feel the potential all around them.",
                    "mechanics": [
                        {
                            "type": "start_project",
                            "effect": "Start a new project."
                        }
                    ]
                }
            ]
        },
        "6": {
            "prompt": None,
            "options": [
                {
                    "text": "Outsiders arrive in the area. Why are they a threat? How are they vulnerable?",
                    "mechanics": []
                },
                {
                    "text": "Outsiders arrive in the area. How many? How are they greeted?",
                    "mechanics": []
                }
            ]
        },
        "7": {
            "prompt": None,
            "options": [
                {
                    "text": "Introduce a mystery at the edge of the map.",
                    "mechanics": []
                },
                {
                    "text": "An unattended situation becomes problematic and scary. What is it? How does it go awry?",
                    "mechanics": []
                }
            ]
        },
        "8": {
            "prompt": None,
            "options": [
                {
                    "text": "Someone tries to take control of the community by force. Do they succeed? Why do they do this?",
                    "mechanics": []
                },
                {
                    "text": "A headstrong community member decides to put one of their ideas in motion.",
                    "mechanics": [
                        {
                            "type": "start_project",
                            "effect": "Start a foolish project."
                        }
                    ]
                }
            ]
        },
        "9": {
            "prompt": None,
            "options": [
                {
                    "text": "A project fails. Which one? Why?",
                    "mechanics": [
                        {
                            "type": "project_management",
                            "effect": "A project fails."
                        }
                    ]
                },
                {
                    "text": "Something goes foul and supplies are ruined.",
                    "mechanics": [
                        {
                            "type": "state_change",
                            "effect": "Add a new Scarcity."
                        }
                    ]
                }
            ]
        },
        "10": {
            "prompt": None,
            "options": [
                {
                    "text": "You discover a cache of supplies or resources.",
                    "mechanics": [
                        {
                            "type": "state_change",
                            "effect": "Add a new Abundance."
                        }
                    ]
                },
                {
                    "text": "A Scarcity has gone unaddressed for too long!",
                    "mechanics": [
                        {
                            "type": "start_project",
                            "effect": "Start a project that will alleviate a Scarcity."
                        }
                    ]
                }
            ]
        },
        "J": {
            "prompt": "Predators and bad omens are afoot.",
            "options": [
                {
                    "text": "You are careless, and someone goes missing under ominous circumstances. Who?",
                    "mechanics": []
                },
                {
                    "text": "What measures do you take to keep everyone safe and under surveillance?",
                    "mechanics": [
                        {
                            "type": "turn_effect",
                            "effect": "Do not reduce project dice this week."
                        }
                    ]
                }
            ]
        },
        "Q": {
            "prompt": "Choose one:",
            "options": [
                {
                    "text": "A project finishes early. Which one? Why?",
                    "mechanics": [
                        {
                            "type": "project_management",
                            "effect": "Finish a project early."
                        }
                    ]
                },
                {
                    "text": "If there are no projects underway, boredom leads to a quarrel. A fight breaks out between two people. What is it about?",
                    "mechanics": []
                }
            ]
        },
        "K": {
            "prompt": "Summer is fleeting.",
            "options": [
                {
                    "text": "Discard the top two cards off the top of the deck and take two actions this week.",
                    "mechanics": [
                        {
                            "type": "deck_management",
                            "effect": "Discard top two cards and allow two actions this turn."
                        }
                    ]
                }
            ]
        }
    },
    "Clubs": {  # Autumn
        "A": {
            "prompt": "The community becomes obsessed with a single project. Which one? Why?",
            "options": [
                {
                    "text": "They decide to take more time to ensure that it is perfect.",
                    "mechanics": [
                        {
                            "type": "project_management",
                            "effect": "Add 3 weeks to the project die."
                        }
                    ]
                },
                {
                    "text": "They drop everything else to work on it.",
                    "mechanics": [
                        {
                            "type": "project_management",
                            "effect": "All other projects fail."
                        }
                    ]
                },
                {
                    "text": "If there are no projects underway, add a Scarcity born of idleness.",
                    "mechanics": [
                        {
                            "type": "condition",
                            "effect": "no_projects_underway"
                        },
                        {
                            "type": "state_change",
                            "effect": "Add a Scarcity born of idleness."
                        }
                    ]
                }
            ]
        },
        "2": {
            "prompt": None,
            "options": [
                {
                    "text": "Someone returns to the community. Who? Where were they?",
                    "mechanics": []
                },
                {
                    "text": "You find a body. Do people recognize who it is? What happened?",
                    "mechanics": []
                }
            ]
        },
        "3": {
            "prompt": None,
            "options": [
                {
                    "text": "Someone leaves the community after issuing a dire warning. Who? What is the warning?",
                    "mechanics": []
                },
                {
                    "text": "Someone issues a dire warning, and the community leaps into action to avoid disaster.",
                    "mechanics": [
                        {
                            "type": "start_project",
                            "effect": "Start a contentious project that relates to the warning."
                        }
                    ]
                }
            ]
        },
        "4": {
            "prompt": None,
            "options": [
                {
                    "text": "The strongest among you dies. What caused the death?",
                    "mechanics": []
                },
                {
                    "text": "The weakest among you dies. Who's to blame for their death?",
                    "mechanics": []
                }
            ]
        },
        "5": {
            "prompt": None,
            "options": [
                {
                    "text": "The Parish arrives. Who are they? Why have they chosen your community, and for what?",
                    "mechanics": []
                },
                {
                    "text": "A small gang of marauders is making its way through local terrain. How many are there? What weapons do they carry?",
                    "mechanics": []
                }
            ]
        },
        "6": {
            "prompt": None,
            "options": [
                {
                    "text": "Introduce a dark mystery among the members of the community.",
                    "mechanics": []
                },
                {
                    "text": "Conflict flares up among community members, and as a result, a project fails.",
                    "mechanics": [
                        {
                            "type": "project_management",
                            "effect": "A project fails."
                        }
                    ]
                }
            ]
        },
        "7": {
            "prompt": "A project just isn't working out as expected.",
            "options": [
                {
                    "text": "Radically change the nature of this project (don't modify the project die). When it resolves, you'll be responsible for telling the community how it went.",
                    "mechanics": [
                        {
                            "type": "project_management",
                            "effect": "Radically change the nature of this project without modifying the project die."
                        }
                    ]
                },
                {
                    "text": "Something goes foul and supplies are ruined.",
                    "mechanics": [
                        {
                            "type": "state_change",
                            "effect": "Add a new Scarcity."
                        }
                    ]
                }
            ]
        },
        "8": {
            "prompt": None,
            "options": [
                {
                    "text": "Someone sabotages a project, and the project fails as a result. Who did this? Why?",
                    "mechanics": [
                        {
                            "type": "project_management",
                            "effect": "A project fails due to sabotage."
                        }
                    ]
                },
                {
                    "text": "Someone is caught trying to sabotage the efforts of the community. How does the community respond?",
                    "mechanics": []
                }
            ]
        },
        "9": {
            "prompt": None,
            "options": [
                {
                    "text": "The community works constantly, and as a result, a project finishes early.",
                    "mechanics": [
                        {
                            "type": "project_management",
                            "effect": "Finish a project early."
                        }
                    ]
                },
                {
                    "text": "A group goes out to explore the map more thoroughly and finds something that had been previously overlooked.",
                    "mechanics": []
                }
            ]
        },
        "10": {
            "prompt": None,
            "options": [
                {
                    "text": "Harvest is here and plentiful.",
                    "mechanics": [
                        {
                            "type": "state_change",
                            "effect": "Add an Abundance."
                        }
                    ]
                },
                {
                    "text": "Cold autumn winds drive out your enemies.",
                    "mechanics": [
                        {
                            "type": "state_change",
                            "effect": "Remove a threatening force from the map and the area."
                        }
                    ]
                }
            ]
        },
        "J": {
            "prompt": None,
            "options": [
                {
                    "text": "A project finishes early. Which one? Why?",
                    "mechanics": [
                        {
                            "type": "project_management",
                            "effect": "Finish a project early."
                        }
                    ]
                },
                {
                    "text": "If there are no projects underway, restlessness creates animosity, which leads to violence. Who gets hurt?",
                    "mechanics": [
                        {
                            "type": "condition",
                            "effect": "no_projects_underway"
                        }
                    ]
                }
            ]
        },
        "Q": {
            "prompt": "Disease spreads through the community. Choose one:",
            "options": [
                {
                    "text": "You spend the week quarantining and treating the disease.",
                    "mechanics": [
                        {
                            "type": "turn_effect",
                            "effect": "Project dice are not reduced this week."
                        }
                    ]
                },
                {
                    "text": "Nobody knows what to do about it.",
                    "mechanics": [
                        {
                            "type": "state_change",
                            "effect": "Add 'Health and Fertility' as a Scarcity."
                        }
                    ]
                }
            ]
        },
        "K": {
            "prompt": "A natural disaster strikes the area. Choose one:",
            "options": [
                {
                    "text": "You focus on getting everyone to safety.",
                    "mechanics": [
                        {
                            "type": "state_change",
                            "effect": "Remove an Abundance."
                        },
                        {
                            "type": "project_management",
                            "effect": "A project fails."
                        }
                    ]
                },
                {
                    "text": "You focus on protecting your supplies and hard work at any cost. Several people die as a result.",
                    "mechanics": []
                }
            ]
        }
    },

    "Spades": {  # Winter
        "A": {
            "prompt": "Now is the time to conserve energy and resources.",
            "options": [
                {
                    "text": "A project fails, but gain an Abundance.",
                    "mechanics": [
                        {
                            "type": "project_management",
                            "effect": "A project fails."
                        },
                        {
                            "type": "state_change",
                            "effect": "Gain an Abundance."
                        }
                    ]
                },
                {
                    "text": "Now is the time for hurried labor and final efforts. A project finishes early, but gain a Scarcity.",
                    "mechanics": [
                        {
                            "type": "project_management",
                            "effect": "A project finishes early."
                        },
                        {
                            "type": "state_change",
                            "effect": "Gain a Scarcity."
                        }
                    ]
                }
            ]
        },
        "2": {
            "prompt": "A headstrong community member takes charge of the community's work efforts.",
            "options": [
                {
                    "text": "A project fails, and then a different project finishes early.",
                    "mechanics": [
                        {
                            "type": "project_management",
                            "effect": "A project fails."
                        },
                        {
                            "type": "project_management",
                            "effect": "A project finishes early."
                        }
                    ]
                },
                {
                    "text": "A headstrong community member tries to take control of the community. How are they prevented from doing this? Due to the conflict, project dice are not reduced this week.",
                    "mechanics": [
                        {
                            "type": "turn_effect",
                            "effect": "Project dice are not reduced this week."
                        }
                    ]
                }
            ]
        },
        "3": {
            "prompt": None,
            "options": [
                {
                    "text": "Someone comes up with an ingenious solution to a big problem, and as a result, a project finishes early. What was their idea?",
                    "mechanics": [
                        {
                            "type": "project_management",
                            "effect": "A project finishes early."
                        }
                    ]
                },
                {
                    "text": "Someone comes up with a plan to ensure safety and comfort during the coldest months. Start a project related to this.",
                    "mechanics": [
                        {
                            "type": "start_project",
                            "effect": "Start a project related to safety and comfort."
                        }
                    ]
                }
            ]
        },
        "4": {
            "prompt": None,
            "options": [
                {
                    "text": "All the animals and young children are crying and won't stop. Hold a discussion about this, in addition to your regular action for this week.",
                    "mechanics": [
                        {
                            "type": "discussion",
                            "effect": "Hold a discussion in addition to your regular action."
                        }
                    ]
                },
                {
                    "text": "A great atrocity is revealed. What is it? Who uncovers it?",
                    "mechanics": []
                }
            ]
        },
        "5": {
            "prompt": None,
            "options": [
                {
                    "text": "Winter elements destroy a food source. If this was your only food source, add a Scarcity.",
                    "mechanics": [
                        {
                            "type": "state_change",
                            "effect": "Add a Scarcity."
                        }
                    ]
                },
                {
                    "text": "Winter elements leave everyone cold, tired, and miserable. Project dice are not reduced this week.",
                    "mechanics": [
                        {
                            "type": "turn_effect",
                            "effect": "Project dice are not reduced this week."
                        }
                    ]
                }
            ]
        },
        "6": {
            "prompt": None,
            "options": [
                {
                    "text": "The time has come to consolidate your efforts and your borders.",
                    "mechanics": [
                        {
                            "type": "project_management",
                            "effect": "Projects outside the settlement fail"
                        },
                        {
                            "type": "turn_effect",
                            "effect": "Projects are reduced by 2."
                        },
                    ]
                },
                {
                    "text": "Someone finds a curious opportunity on the edge of the map. Start a project related to this discovery.",
                    "mechanics": [
                        {
                            "type": "start_project",
                            "effect": "Start a project related to the discovery."
                        }
                    ]
                }
            ]
        },
        "7": {
            "prompt": "What is winter like in this area? How do community members react to the weather?",
            "options": []
        },
        "8": {
            "prompt": "Winter is harsh, and desperation gives rise to fear-mongering. Choose one:",
            "options": [
                {
                    "text": "Spend the week calming the masses and dispelling their violent sentiments. The week ends immediately.",
                    "mechanics": [
                        {
                            "type": "turn_effect",
                            "effect": "The week ends immediately."
                        }
                    ]
                },
                {
                    "text": "Declare war on someone or something. This counts as starting a project.",
                    "mechanics": [
                        {
                            "type": "start_project",
                            "effect": "Declare war on someone or something."
                        }
                    ]
                }
            ]
        },
        "9": {
            "prompt": "Someone goes missing. They're alone in the winter elements. Choose one:",
            "options": [
                {
                    "text": "The community organizes constant search parties and eventually the person is found. Project dice are not reduced this week.",
                    "mechanics": [
                        {
                            "type": "turn_effect",
                            "effect": "Project dice are not reduced this week."
                        }
                    ]
                },
                {
                    "text": "No one ever hears from that person again.",
                    "mechanics": []
                }
            ]
        },
        "10": {
            "prompt": None,
            "options": [
                {
                    "text": "In preparation for the coming year, the community begins a huge undertaking. Start a project that will take at least 5 weeks to complete.",
                    "mechanics": [
                        {
                            "type": "start_project",
                            "effect": "Start a project that lasts at least 5 weeks."
                        }
                    ]
                }
            ]
        },
        "J": {
            "prompt": "An infected outsider arrives, seeking amnesty. They have some much-needed resources with them. Choose one:",
            "options": [
                {
                    "text": "Welcome them into the community. Remove a Scarcity, but also introduce an infection into the community.",
                    "mechanics": [
                        {
                            "type": "state_change",
                            "effect": "Remove a Scarcity."
                        },
                        {
                            "type": "state_change",
                            "effect": "Introduce an infection into the community."
                        }
                    ]
                },
                {
                    "text": "Bar them from entry. What Scarcity could they have addressed? How does its need become more dire this week?",
                    "mechanics": []
                }
            ]
        },
        "Q": {
            "prompt": None,
            "options": [
                {
                    "text": "You see a good omen. What is it?",
                    "mechanics": []
                }
            ]
        },
        "K": {
            "prompt": "The Frost Shepherds arrive.",
            "options": [
                {
                    "text": "The game is over.",
                    "mechanics": [
                        {
                            "type": "end_game",
                            "effect": "The game ends immediately."
                        }
                    ]
                }
            ]
        }
    }
}