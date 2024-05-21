import torch
import os
import six
import sentencepiece as spm


def convert_to_unicode(text):
    """Converts `text` to Unicode (if it's not already), assuming utf-8 input."""
    return six.ensure_text(text, errors="ignore")


class YalmTokenizer:
    NEW_LINE = "[NL]"
    UNK = 0
    BOS = 1
    EOS = 2
    BOS_TOKEN = "<s>"
    EOS_TOKEN = "</s>"
    MASK_TOKEN = "[MASK]"

    def __init__(self, vocab_file):
        self.name = "sp"
        self._tokenizer = spm.SentencePieceProcessor(
            model_file=vocab_file,
        )
        self._vocab_words = self._get_vocab_words()
        self.encoder = {token: idx for idx, token in enumerate(self._vocab_words)}
        self.decoder = {idx: token for idx, token in enumerate(self._vocab_words)}
        self.padding_side = 'left'
        self.truncation_side = 'left'
        self.model_max_length = 2049
        
        self.bos_token = "<s>"
        self.eos_token = "</s>"
        self.pad_token = "<s>"
        
        mask_tokens = self.convert_tokens_to_ids([self.MASK_TOKEN])
        assert len(mask_tokens) == 1
        self.MASK = mask_tokens[0]
        
    @classmethod
    def from_pretrained(cls, path):
        return cls(os.path.join(path, 'voc_100b.sp'))

    def _encode(self, line, out_type=str):
        return self._tokenizer.encode(line, out_type=out_type)

    def tokenize(self, line, out_type=int):
        line = convert_to_unicode(line)
        line = line.replace("\n", self.NEW_LINE)
        has_bos = False
        has_eos = False
        if line.startswith('<s> '):
            has_bos = True
            line = line[4:]
        elif line.startswith('<s>'):
            has_bos = True
            line = line[3:]
        if line.endswith(' </s>'):
            has_eos = True
            line = line[:-5]
        elif line.endswith('</s>'):
            has_eos = True
            line = line[:-4]
    
        token_ids = self._encode(line, out_type=out_type)

        if has_bos:
            if out_type == int:
                token_ids = [1] + token_ids
            else:
                token_ids = [self.bos_token] + token_ids
        if has_eos:
            if out_type == int:
                token_ids = token_ids + [2]
            else:
                token_ids = token_ids + [self.eos_token]

        return token_ids
    
    def convert_tokens_to_ids(self, tokens):
        return self._tokenizer.piece_to_id(tokens)

    def convert_ids_to_tokens(self, ids):
        if isinstance(ids, int):
            return self.decoder[ids]
        if isinstance(ids, torch.Tensor):
            ids = ids.cpu().tolist()
        return [self.decoder[idx] for idx in ids]

    def get_tokens(self):
        return self._vocab_words

    def _get_vocab_words(self):
        indices = list(range(self._tokenizer.GetPieceSize()))
        return self._tokenizer.id_to_piece(indices)

    @property
    def vocab(self):
        return self.encoder

    @property
    def inv_vocab(self):
        return self.decoder

    @property
    def vocab_size(self):
        return len(self.encoder)

    def detokenize(self, token_ids):
        tokens = [self.decoder[idx] for idx in token_ids]
        text = "".join(tokens).replace("\u2581", " ").replace(self.EOS_TOKEN, "").lstrip()
        return text

    @property
    def cls(self):
        return self.BOS

    @property
    def eod(self):
        return self.EOS

    @property
    def mask(self):
        return self.MASK
    
    def __call__(self, text, return_tensors='pt', padding='max_length', truncation=True, add_bos=True):
        
        assert return_tensors == 'pt'
        assert padding == 'max_length' or padding == True
        
        if isinstance(text, str):
            text = [text]
            
        ids = []
        for t in text:
            if t.startswith('<s> '):
                t_ids = self.tokenize(t[4:])
                t_ids = [1] + t_ids
            elif t.startswith('<s>'):
                t_ids = self.tokenize(t[3:])
                t_ids = [1] + t_ids
            else:
                t_ids = self.tokenize(t)
                if add_bos:
                    t_ids = [1] + t_ids # append <s>
            
            if truncation:
                if self.truncation_side == 'left':
                    t_ids = t_ids[-self.model_max_length:]
                else:
                    t_ids = t_ids[:self.model_max_length]
            
            ids.append(t_ids)
        
        if padding != 'max_length':
            max_len = max([len(t_ids) for t_ids in ids])
        else:
            max_len = self.model_max_length
        
        attention_mask = torch.ones(len(ids), max_len, dtype=torch.long)
        
        if self.padding_side == 'left':
            new_ids = []
            for i, t_ids in enumerate(ids):
                attention_mask[i, :max_len - len(t_ids)] = 0
                new_ids.append([self.BOS]*(max_len - len(t_ids)) + t_ids)
        else:
            new_ids = []
            for i, t_ids in enumerate(ids):
                attention_mask[i, -(max_len - len(t_ids)):] = 0
                new_ids.append(t_ids + [self.EOS]*(max_len - len(t_ids)))
        ids = new_ids
        ids = torch.tensor(ids)
        
        if add_bos:
            # make sure starts with <s>
            ids[:, 0] = 1
        
        return {
            'input_ids': ids, 'attention_mask': attention_mask
        }
        
    def decode(self, token_ids):
        if isinstance(token_ids, torch.Tensor):
            token_ids = token_ids.cpu().tolist()
        return self.detokenize(token_ids).replace(self.NEW_LINE, "\n")