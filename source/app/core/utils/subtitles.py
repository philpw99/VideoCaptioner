from ...common.config import INVISIBLE_ORIGINAL,INVISIBLE_TRANSLATED

def get_original_and_translated(text) -> list[str, str]:
    original, translated = "", ""
    lines = text.split("\n")
    trans_mode = False
    for line in lines:
        if line[0] == INVISIBLE_ORIGINAL:
            trans_mode = False  # Now the rest lines are original
            line = line[1:]
        elif line[0] == INVISIBLE_TRANSLATED:
            trans_mode = True   # Now the rest lines are translated
            line = line[1:]
        
        if trans_mode:
            translated = line if not translated else translated + "\n" + line
        else:
            original = line if not original else original + "\n" + line
            
    return original, translated
