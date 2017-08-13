from utils import load_names_file


def load_acronym_to_name(acronym_name_file, exclude_strs):
    acr_name_dict = dict()
    f = open(acronym_name_file, 'r')
    for line in f:
        line = line.strip().decode('utf-8')
        acr, name, _ = line.split('\t')

        if exclude_strs and acr in exclude_strs:
            continue

        acr_name_dict[acr] = name
        # print acr, name_max

    f.close()

    return acr_name_dict


def load_name_to_acronym(acronym_name_file, abbrev_exclude_strs):
    name_acr_cnt_dict = dict()
    f = open(acronym_name_file, 'r')
    for line in f:
        line = line.strip().decode('utf-8')
        acr, name, cnt = line.split('\t')
        if name in abbrev_exclude_strs:
            continue

        cnt = int(cnt)

        tup = name_acr_cnt_dict.get(name, None)
        if not tup or tup[1] < cnt:
            name_acr_cnt_dict[name] = (acr, cnt)
        # print acr, name_max
    f.close()

    name_acr_dict = dict()
    for name, (acr, cnt) in name_acr_cnt_dict.iteritems():
        name_acr_dict[name] = acr

    return name_acr_dict


def expand_word(word, acr_name_dict):
    name_exp = ''
    pl = 0
    while pl < len(word):
        pr = len(word)
        exps = ''
        while pr > pl:
            exps = acr_name_dict.get(word[pl:pr], None)
            if exps:
                break
            pr -= 1

        if pr > pl:
            name_exp += exps
            pl = pr
        else:
            name_exp += word[pl]
            pl = pr + 1

    return name_exp


class QueryExpansion:
    def __init__(self, acronym_name_file, extra_acronym_name_file, expand_exclude_strs_file,
                 abbrev_exclude_strs_file, cn_seg_app):
        self.expand_exclude_strs = load_names_file(expand_exclude_strs_file)
        self.acr_name_dict = load_acronym_to_name(acronym_name_file, self.expand_exclude_strs)

        self.abbrev_exclude_strs = load_names_file(abbrev_exclude_strs_file)
        self.name_acr_dict = load_name_to_acronym(acronym_name_file, self.abbrev_exclude_strs)

        self.__load_extra_acronym_name_file(extra_acronym_name_file)

        self.seg_app = cn_seg_app

    def __load_extra_acronym_name_file(self, filename):
        f = open(filename)
        for line in f:
            acr, name = line.strip().decode('utf-8').split('\t')
            self.acr_name_dict[acr] = name
            self.name_acr_dict[name] = acr
        f.close()

    def __expand_name_words_ob(self, name_words):
        name_exp = ''
        lw = len(name_words)
        l = 0
        while l < lw:
            r = lw
            cur_str = ''
            while r > l:
                cur_str = ''.join(name_words[l:r])
                if cur_str in self.expand_exclude_strs:
                    break
                r -= 1

            if r > l:
                name_exp += cur_str
                l = r
            else:
                name_exp += expand_word(name_words[l], self.acr_name_dict)
                print name_words[l], name_exp
                l += 1
        return name_exp

    def __expand_name_words(self, name_words):
        name_exp = ''
        lw = len(name_words)
        l = 0
        while l < lw:
            r = lw
            flg = True
            while r > l:
                cur_str = ''.join(name_words[l:r])
                if cur_str in self.expand_exclude_strs:
                    name_exp += cur_str
                    l = r
                    flg = False
                    break

                str_exp = self.acr_name_dict.get(cur_str, '')
                if str_exp:
                    name_exp += str_exp
                    l = r
                    flg = False
                    break

                r -= 1

            if flg:
                name_exp += expand_word(name_words[l], self.acr_name_dict)
                # print name_words[l], name_exp
                l += 1
        return name_exp

    def __abbrev_name_words(self, name_words):
        new_name = ''
        wlen = len(name_words)
        l = 0
        while l < wlen:
            r = wlen
            flg = False
            while r > l:
                cur_str = ''.join(name_words[l:r])
                str_acr = self.name_acr_dict.get(cur_str, '')
                if str_acr:
                    new_name += str_acr
                    l = r
                    flg = True
                    break
                r -= 1
            if not flg:
                new_name += name_words[l]
                l += 1

        return new_name

    def query_expansion_words(self, name_words):
        name_expand = self.__expand_name_words(name_words)
        name_abbrev = self.__abbrev_name_words(name_words)

        exp_names = []
        if name_expand:
            exp_names.append(name_expand)
        if name_abbrev:
            exp_names.append(name_abbrev)
        return exp_names

    def query_expansion(self, name_str):
        name_words = self.seg_app.segment(name_str).split(' ')
        name_expand = self.__expand_name_words(name_words)
        name_abbrev = self.__abbrev_name_words(name_words)

        exp_cands = [name_expand, name_abbrev]
        exp_names = list()
        for name in exp_cands:
            if len(name) == len(name_str) - name_str.count(' '):
                continue
            if name != name_str:
                exp_names.append(name)
        return exp_names

    def expand_name(self, name_str):
        words = self.seg_app.segment(name_str).split(' ')

        new_name = self.__expand_name_words(words)
        if new_name != name_str:
            return new_name
        return ''

    def abbrev_name(self, name_str):
        words = self.seg_app.segment(name_str).split(' ')

        new_name = self.__abbrev_name_words(words)

        if len(new_name) == len(name_str) - 1 and ' ' in name_str:
            return ''

        if new_name != name_str:
            return new_name
        return ''
