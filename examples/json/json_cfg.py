from typing import Tuple

_LIST = "        return ParserNode([value, *list_elems2_list])"
_DICT = "        return ParserNode([pair, *dict_pairs2_list])"


class JSONParserActions:
    def list_elems(self) -> Tuple[str, str]:
        return _LIST, "TreeNode"

    def dict_pairs(self) -> Tuple[str, str]:
        return _DICT, "TreeNode"


parser_actions = JSONParserActions()
memoize = True
