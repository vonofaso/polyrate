from aiogram.fsm.state import State, StatesGroup


class RatingStates(StatesGroup):
    choosing_teacher = State()
    searching_teacher = State()
    answering_professional_orientation = State()
    answering_digital_resources = State()
    answering_clear_requirements = State()
    answering_fair_assessment = State()
    answering_individual_approach = State()
    answering_clear_explanation = State()
    answering_organization = State()
    answering_willingness_to_help = State()
    answering_communication = State()
    answering_respect = State()
    answering_positive_climate = State()
    choosing_tags = State()
    writing_comment = State()