import re
import math
from collections import Counter
from typing import List, Tuple, Dict, Any


class BLEU:
    """
    BLEU (Bilingual Evaluation Understudy) 评估指标
    用于评估生成文本与参考文本的相似度
    """
    
    def __init__(self, n_gram=4):
        """
        初始化 BLEU 评估器
        
        Args:
            n_gram: 最大 n-gram 长度
        """
        self.n_gram = n_gram
    
    def _get_ngrams(self, text: str, n: int) -> Counter:
        """
        获取文本的 n-gram 计数
        
        Args:
            text: 输入文本
            n: n-gram 长度
            
        Returns:
            Counter: n-gram 计数
        """
        # 对于中文，直接按字符分割，不使用正则分词
        # 对于英文，使用正则分词
        if any(ord(c) > 127 for c in text):
            # 中文文本，按字符分割
            tokens = list(text)
        else:
            # 英文文本，使用正则分词
            tokens = re.findall(r'\b\w+\b', text.lower())
        
        if len(tokens) < n:
            return Counter()
        return Counter([''.join(tokens[i:i+n]) for i in range(len(tokens)-n+1)])
    
    def _brevity_penalty(self, candidate_len: int, reference_len: int) -> float:
        """
        计算 brevity penalty
        
        Args:
            candidate_len: 候选文本长度
            reference_len: 参考文本长度
            
        Returns:
            float: brevity penalty 值
        """
        if candidate_len > reference_len:
            return 1.0
        elif candidate_len == 0:
            return 0.0
        else:
            return math.exp(1 - reference_len / candidate_len)
    
    def calculate(self, candidate: str, references: List[str]) -> float:
        """
        计算 BLEU 分数
        
        Args:
            candidate: 候选文本
            references: 参考文本列表
            
        Returns:
            float: BLEU 分数
        """
        if not candidate:
            return 0.0
        
        # 计算候选文本和参考文本的长度
        candidate_tokens = re.findall(r'\b\w+\b', candidate.lower())
        candidate_len = len(candidate_tokens)
        
        reference_lens = []
        reference_ngrams = []
        
        for ref in references:
            ref_tokens = re.findall(r'\b\w+\b', ref.lower())
            reference_lens.append(len(ref_tokens))
            ref_ngram_list = []
            for n in range(1, self.n_gram + 1):
                ref_ngram_list.append(self._get_ngrams(ref, n))
            reference_ngrams.append(ref_ngram_list)
        
        # 选择最接近候选文本长度的参考文本
        best_ref_idx = min(range(len(reference_lens)), key=lambda i: abs(reference_lens[i] - candidate_len))
        best_ref_len = reference_lens[best_ref_idx]
        best_ref_ngrams = reference_ngrams[best_ref_idx]
        
        # 计算 brevity penalty
        bp = self._brevity_penalty(candidate_len, best_ref_len)
        
        # 计算各 n-gram 的精确率
        precisions = []
        for n in range(1, self.n_gram + 1):
            candidate_ngram = self._get_ngrams(candidate, n)
            if not candidate_ngram:
                precisions.append(0.0)
                continue
            
            ref_ngram = best_ref_ngrams[n-1]
            overlap = sum((candidate_ngram & ref_ngram).values())
            precision = overlap / sum(candidate_ngram.values())
            precisions.append(precision)
        
        # 计算几何平均
        # 避免因为任何一个n-gram的精确率为0而导致整个分数为0
        # 只考虑那些有非零精确率的n-gram
        non_zero_precisions = [p for p in precisions if p > 0]
        if not non_zero_precisions:
            return 0.0
        
        geometric_mean = math.exp(sum(math.log(p) for p in non_zero_precisions) / len(non_zero_precisions))
        bleu_score = bp * geometric_mean
        
        return bleu_score


class ROUGE:
    """
    ROUGE (Recall-Oriented Understudy for Gisting Evaluation) 评估指标
    用于评估生成文本与参考文本的重叠度
    """
    
    def __init__(self):
        """
        初始化 ROUGE 评估器
        """
        pass
    
    def _get_ngrams(self, text: str, n: int) -> Counter:
        """
        获取文本的 n-gram 计数
        
        Args:
            text: 输入文本
            n: n-gram 长度
            
        Returns:
            Counter: n-gram 计数
        """
        # 对于中文，直接按字符分割，不使用正则分词
        # 对于英文，使用正则分词
        if any(ord(c) > 127 for c in text):
            # 中文文本，按字符分割
            tokens = list(text)
        else:
            # 英文文本，使用正则分词
            tokens = re.findall(r'\b\w+\b', text.lower())
        
        if len(tokens) < n:
            return Counter()
        return Counter([''.join(tokens[i:i+n]) for i in range(len(tokens)-n+1)])
    
    def _longest_common_subsequence(self, a: List[str], b: List[str]) -> int:
        """
        计算最长公共子序列长度
        
        Args:
            a: 第一个序列
            b: 第二个序列
            
        Returns:
            int: 最长公共子序列长度
        """
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if a[i-1] == b[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        return dp[m][n]
    
    def calculate(self, candidate: str, references: List[str]) -> Dict[str, float]:
        """
        计算 ROUGE 分数
        
        Args:
            candidate: 候选文本
            references: 参考文本列表
            
        Returns:
            Dict[str, float]: ROUGE 分数字典
        """
        if not candidate:
            return {
                'rouge-1': 0.0,
                'rouge-2': 0.0,
                'rouge-l': 0.0
            }
        
        # 对于中文，直接按字符分割，不使用正则分词
        # 对于英文，使用正则分词
        if any(ord(c) > 127 for c in candidate):
            # 中文文本，按字符分割
            candidate_tokens = list(candidate)
        else:
            # 英文文本，使用正则分词
            candidate_tokens = re.findall(r'\b\w+\b', candidate.lower())
        candidate_len = len(candidate_tokens)
        
        scores = {
            'rouge-1': 0.0,
            'rouge-2': 0.0,
            'rouge-l': 0.0
        }
        
        for ref in references:
            # 对于中文，直接按字符分割，不使用正则分词
            # 对于英文，使用正则分词
            if any(ord(c) > 127 for c in ref):
                # 中文文本，按字符分割
                ref_tokens = list(ref)
            else:
                # 英文文本，使用正则分词
                ref_tokens = re.findall(r'\b\w+\b', ref.lower())
            ref_len = len(ref_tokens)
            
            if ref_len == 0:
                continue
            
            # 计算 ROUGE-1
            candidate_ngram_1 = self._get_ngrams(candidate, 1)
            ref_ngram_1 = self._get_ngrams(ref, 1)
            overlap_1 = sum((candidate_ngram_1 & ref_ngram_1).values())
            rouge_1 = overlap_1 / ref_len
            
            # 计算 ROUGE-2
            candidate_ngram_2 = self._get_ngrams(candidate, 2)
            ref_ngram_2 = self._get_ngrams(ref, 2)
            overlap_2 = sum((candidate_ngram_2 & ref_ngram_2).values())
            rouge_2 = overlap_2 / max(1, ref_len - 1)
            
            # 计算 ROUGE-L
            lcs = self._longest_common_subsequence(candidate_tokens, ref_tokens)
            rouge_l = lcs / ref_len
            
            # 更新最高分数
            scores['rouge-1'] = max(scores['rouge-1'], rouge_1)
            scores['rouge-2'] = max(scores['rouge-2'], rouge_2)
            scores['rouge-l'] = max(scores['rouge-l'], rouge_l)
        
        return scores


class TextEvaluator:
    """
    文本评估器，整合 BLEU 和 ROUGE 评估指标
    """
    
    def __init__(self):
        """
        初始化文本评估器
        """
        self.bleu = BLEU()
        self.rouge = ROUGE()
    
    def evaluate(self, candidate: str, references: List[str]) -> Dict[str, float]:
        """
        评估生成文本
        
        Args:
            candidate: 生成的文本
            references: 参考文本列表
            
        Returns:
            Dict[str, float]: 评估指标字典
        """
        if not references:
            return {
                'bleu': 0.0,
                'rouge-1': 0.0,
                'rouge-2': 0.0,
                'rouge-l': 0.0
            }
        
        # 添加调试信息
        print(f"评估器收到的候选文本: {candidate[:50]}...")
        print(f"评估器收到的参考文本: {references[0][:50]}...")
        
        bleu_score = self.bleu.calculate(candidate, references)
        rouge_scores = self.rouge.calculate(candidate, references)
        
        print(f"BLEU分数: {bleu_score}")
        print(f"ROUGE分数: {rouge_scores}")
        
        return {
            'bleu': bleu_score,
            **rouge_scores
        }


# 全局评估器实例
evaluator = TextEvaluator()
