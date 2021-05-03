from typing import Tuple

_LIST = "        return ParserNode([value, *list_sub2_depth2_list])"
_DICT = "        return ParserNode([pair, *dict_sub2_depth2_list])"


class JSONParserActions:
    def list_sub1_depth1(self) -> Tuple[str, str]:
        return _LIST, "TreeNode"

    def dict_sub1_depth1(self) -> Tuple[str, str]:
        return _DICT, "TreeNode"


parser_actions = JSONParserActions()
memoize = True
