import concurrent.futures
import time
from pydantic import BaseModel
from typing import List, Union, Dict, Optional, Literal

from utils.constants import MAX_CONTEXTS, LLM_MAX_TOKENS, NOT_ENOUGH_INFO_ANSWER
from langchain.llms import OpenAIChat
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.text_splitter import CharacterTextSplitter
import tiktoken
from copy import deepcopy
import json
from bs4 import BeautifulSoup
from utils.constants import ENVIRONMENT


class CiteSpan(BaseModel):
    start: int
    end: int
    text: str
    ref_id: Optional[str]


class TextBlock(BaseModel):
    text: str
    section: str
    sec_num: Union[int, None, str]
    cite_spans: List[CiteSpan]
    ref_spans: List[CiteSpan]


class FigRef(BaseModel):
    fig_num: Optional[str]
    text: str
    type_str: Literal["figure"]
    uris: Optional[List[str]]


class TabRef(BaseModel):
    text: str
    type_str: Literal["table"]
    content: Optional[str]
    num: Optional[int]


class PdfParse(BaseModel):
    body_text: List[TextBlock]
    back_matter: List[TextBlock]
    ref_entries: Dict[str, Union[FigRef, TabRef]]

class Location(BaseModel):
    settlement: Optional[str]
    country: Optional[str]

class Affiliation(BaseModel):
    laboratory: Optional[str]
    institution: Optional[str]
    location: Optional[Location]

class Author(BaseModel):
    first: str
    middle: List[str]
    last: str
    suffix: str
    affiliation: Optional[Affiliation]
    email: Optional[str]

class Paper(BaseModel):
    abstract: str
    title: str
    authors: Optional[List[Author]]
    pdf_parse: PdfParse

    def get_sections(self) -> List[str]:
        sections = set()
        if self.abstract:
            sections.add('Abstract')
        if self.title:
            sections.add('Title')
        if self.pdf_parse:
            pdf_parse: PdfParse = self.pdf_parse
            if pdf_parse.body_text:
                for text_block in pdf_parse.body_text:
                    if text_block.section:
                        sections.add(text_block.section)
            if pdf_parse.back_matter:
                for text_block in pdf_parse.back_matter:
                    if text_block.section:
                        sections.add(text_block.section)
        return list(sections)

    def _get_ref_entries_in_text_blocks(self, sections: List[TextBlock]) -> Dict[str, FigRef]:
        ref_entries = {}
        for section in sections:
            for ref_span in section.ref_spans:
                ref_id = ref_span.ref_id
                if ref_id is None:
                    continue
                if ref_id in self.pdf_parse.ref_entries:
                    ref_entries[ref_id] = self.pdf_parse.ref_entries[ref_id]
        return ref_entries

    def filter_sections(self, mode: str, paper_sections_partially_matches: List[str]):
        print(
            f"Filtering paper sections to {mode} {paper_sections_partially_matches}")
        new_paper = deepcopy(self)
        if mode not in ['include', 'exclude']:
            raise ValueError("Mode must be either 'include' or 'exclude'")
        # Create a set of section names to match against
        match_set = set(paper_sections_partially_matches)

        # Filter out text blocks whose section names don't partially match
        filtered_blocks = []
        for block in new_paper.pdf_parse.body_text:
            if any(match.lower() in block.section.lower() for match in match_set):
                filtered_blocks.append(block)

        filtered_back_matters = []
        for block in new_paper.pdf_parse.back_matter:
            if any(match.lower() in block.section.lower() for match in match_set):
                filtered_back_matters.append(block)

        # If we're excluding, we want to inverse the filter
        if mode == "exclude":
            filtered_blocks = [
                block for block in new_paper.pdf_parse.body_text if block not in filtered_blocks]
            filtered_back_matters = [
                block for block in new_paper.pdf_parse.back_matter if block not in filtered_back_matters]

        if filtered_blocks == filtered_back_matters == []:
            print("Filtered was too harsh! Paper went blank! Returning original")
            return

        ref_entries = self._get_ref_entries_in_text_blocks(
            [*filtered_blocks, *filtered_back_matters])

        del self.pdf_parse

        filtered_paper = Paper(
            **self.dict(),
            pdf_parse=PdfParse(
                body_text=filtered_blocks,
                back_matter=filtered_back_matters,
                ref_entries=ref_entries
            )
        )

        self.__dict__.update(filtered_paper.__dict__)

    def format_authors(self) -> str:
        result = []
        for author in self.authors:
            author_s = f"{author.first} {author.last}"
            if 'affiliation' in author and 'institution' in author.affiliation :
                author_s += f", {author.affiliation.institution}"
            if 'affliation' in author and 'location' in author.affiliation and 'country' in author.affiliation.location:
                author_s += f", {author.affiliation.location.country}"
            
            result.append(author_s)

        return "\n".join(result)
    

    def to_text(self) -> str:
        sections = set()
        result = []

        result.append(f"# {self.title}")

        if self.authors:
            result.append(f"Authors: {self.format_authors()}")

        encode_section_header = lambda x: "#" * (x.count(".") + 1) if x and x[-1] != "." else "-"

        for text_block in self.pdf_parse.body_text + self.pdf_parse.back_matter:
            section = f"{encode_section_header(str(text_block.sec_num))} {text_block.sec_num or ''} {text_block.section}"
            if section not in sections:
                result.append(f"{section}\n{text_block.text}")
                sections.add(section)
            else:
                result[-1] += f"\n{text_block.text}"

        figs_and_tables = []
        for key, ref in self.pdf_parse.ref_entries.items():
            if ref.type_str == "figure":
                fig_num = ref.fig_num if ref.fig_num else key.replace(
                    "FIGREF", "")
                if fig_num == "0":
                    fig_num = ""
                figs_and_tables.append(f"Figure {fig_num} caption: \"{ref.text}\"")
            elif ref.type_str == "table":
                table_num = ref.num if ref.num else key.replace("TABREF", "")
                if table_num == "0":
                    table_num = ""
                figs_and_tables.append(
                    f"Table {table_num}: {ref.text}\n{html_table_to_markdown(ref.content)}")

        if figs_and_tables != []:
            result.append(f"#### Figures and Tables")
            result.extend(figs_and_tables)

        return '\n\n'.join(result)


def html_table_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    headers = [th.get_text().strip() for th in table.find_all("th")]
    rows = []
    for tr in table.find_all("tr"):
        row = [td.get_text().strip() for td in tr.find_all("td")]
        if row:
            rows.append(row)
    md_table = ""
    md_table += "| " + " | ".join(headers) + " |\n" if headers != [] else ""
    md_table += "| " + \
        " | ".join(["---" for _ in headers]) + " |\n" if headers != [] else ""
    for index, row in enumerate(rows):
        md_table += "| " + " | ".join(row) + " |\n"

        if headers == [] and index == 0:
            md_table += "| " + " | ".join(["---" for _ in row]) + " |\n"

    return md_table


def count_tokens(text) -> int:
    if text is None:
        return 0
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo-0301")
    result = int(len(enc.encode(text, disallowed_special=())))# Add % as apparently the tokenizer is not 100% accurate
    return result 

def decode(tokens) -> str:
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo-0301")
    return enc.decode(tokens)


def split_text(text, chunk_size=3500):
    text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=chunk_size, chunk_overlap=20, separator="\n")
    texts = text_splitter.split_text(text)
    return texts


def ask_text(text, completion_tokens=None):
    if count_tokens(text) > LLM_MAX_TOKENS:
        raise ValueError("Text is too long, must be less than " +
                         str(LLM_MAX_TOKENS) + " tokens")
    
    if completion_tokens is None:
        completion_tokens = LLM_MAX_TOKENS - count_tokens(text)

    llm = OpenAIChat(temperature=0, max_tokens=completion_tokens)

    prompt = PromptTemplate(input_variables=[], template=text)

    chain = LLMChain(llm=llm, prompt=prompt)
    return chain.run(irrelevant="")


def get_top_k_sections(k, text, labels):
    if len(labels) < k:
        print(f"Already has less than {k} sections, skipping")
        return labels

    print(f"Getting top {k} labels")
    # Fetch it from LLMs since multi-class
    start = time.time()
    result = ask_text(f"""
        Give me a shortened list of the most relevant sections for the following text. 
        Text: {text}
        Sections: {str(labels)}
        Most relevant {k} sections in JSON array format:
        """)
    end = time.time()
    print("Result: " + result)
    print("Time taken to top k labels: " + str(end - start) + " seconds")
    try:
        return json.loads(result)
    except json.JSONDecodeError as e:
        print("Failed to parse result as JSON, returning all labels")
        return labels


async def ask_paper(question: str, paper: Paper, merge_at_end=True, results_speed_trade_off: int = 0):
    print("Asking paper")
    switcher = {
        0: None,
        1: 20,
        2: 14,
        3: 8,
        4: 3
    }
    top_k_sections = switcher.get(results_speed_trade_off, "invalid")
    if top_k_sections == "invalid":
        raise ValueError(
            "Invalid valid for speed_acc_trade_off, must be one of " + str(list(switcher.keys())))

    if switcher.get(results_speed_trade_off) is not None:
        selected_sections = get_top_k_sections(
            k=top_k_sections, text=f"Question on paper article {paper.title}: {question}", labels=paper.get_sections())
        print("Selected sections: " + str(selected_sections))
        paper.filter_sections('include', selected_sections)

    if "this is a load test" in question.lower():
        return "This is a load test response"

    paper.filter_sections(
        'exclude', ['reference', 'acknow', 'appendi', 'decl', 'supp', 'funding'])

    prompt = PromptTemplate(
        input_variables=["context", "request"],
        template=f"""Please respond to the following request, denoted by "Request" in the best way possible with the
            given paper context that bounded by the paper context (it can be the full or a subpart of the paper).
            The context you're receiving is only a part of the paper, so, if the partial paper context does not enough information for confidently respond to the request, please respond with 
            \"{NOT_ENOUGH_INFO_ANSWER}\".
            Your answer must only include information that is explicitly present in the paper context.
            Your answer must not include ANY links that are not present in the paper context.
            Your answer must not include ANY numbers that are not exactly present in the paper context.
            Start paper context:
            {{context}}
            :End paper context.
            Request: '{{request}}'
            Response:
            """,
    )

    completion_tokens = 700
    context_max_tokens = LLM_MAX_TOKENS - \
        completion_tokens - count_tokens(prompt.template)
    print(f"context_max_tokens: {context_max_tokens}")

    full_context = paper.to_text()

    while True:
        contexts = split_text(full_context, context_max_tokens)

        context_sizes = [count_tokens(context) for context in contexts]
        print("Context sizes: ", context_sizes)

        sequence_sizes = [context_size + count_tokens(
            prompt.template + question) + completion_tokens for context_size in context_sizes]
        print("Sequence sizes: ", sequence_sizes)

        if max(sequence_sizes) > LLM_MAX_TOKENS:
            print("Sequences too big! Shortening..")
            completion_tokens -= 60
            context_max_tokens -= 200
        else:
            break

    if ENVIRONMENT == "dev":
        with open("paper.txt", "w") as f:
            f.write(full_context)
        with open("contexts.txt", "w") as f:
            f.write("\n".join(["\nContext nr " + str(i) + ": " + context + '\n' for i, context in enumerate(contexts)]))


    llm = OpenAIChat(temperature=0, max_tokens=completion_tokens)
    chain = LLMChain(llm=llm, prompt=prompt)

    def wrapper(request, context, index):
        print("Running chain nr " + str(index))
        start = time.time()
        result = chain.run(request=request, context=context)
        elapsed_time = time.time() - start
        print(
            f"Elapsed time for chain nr {str(index)}: {elapsed_time:.2f} seconds")
        return result

    futures = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for index, context in enumerate(contexts[:MAX_CONTEXTS]):
            futures.append(executor.submit(
                wrapper, request=question, context=context, index=index))

    responses = [f.result() for f in futures]


    if (len(responses) > 1):
        if merge_at_end:
            summary_prompt = PromptTemplate(
                input_variables=["responses", "question"],
                template="""Please merge the following responses (denoted by 'Response N:').
                        All of these different responses were generated by taking into account only different parts of the paper. Hence they can be wrong.
                        You should merge them into a single response, using only the ones that positively answer the initial question.
                        There a few important caveats that you must follow:
                        - You should duplicate any information that positively answers the initial question.
                        - You keep its sequentiality (i.e 'Response N+1' contents come after 'Response N').
                        - You must keep the style of the original responses (if for example they are all markdown tables, your response should be a markdown table too)
                        - If you include web links they must be exactely matching the link in it's original response.
                        Your final answer must be a single response that answers the initial question, uninteligible that it is a merge of multiple responses.
                        {responses}
                        Initial Question:
                        {question}
                        Response:
                        """,
            )
            summary_prompt_length = count_tokens(summary_prompt.template) + sum(
                [count_tokens(response) for response in responses]) + count_tokens(question)
            print("Summary prompt length: ",  + summary_prompt_length)
            llm = OpenAIChat(temperature=0, max_tokens=max(
                1000, LLM_MAX_TOKENS - summary_prompt_length))
            chain = LLMChain(llm=llm, prompt=summary_prompt)
            responses = [f"\n Response {i}: \n" +
                         r for i, r in enumerate(responses)]

            start = time.time()
            response = chain.run(responses='\n'.join(
                responses), question=question)
            end = time.time()
            print("Time taken to merge responses: " + str(end - start) + " seconds")
        else:
            response = "\n".join(responses)
        responses.append(response)

    if NOT_ENOUGH_INFO_ANSWER in responses[-1] and results_speed_trade_off > 0:
        return await ask_paper(question, paper, results_speed_trade_off - 1, merge_at_end)
    
    if ENVIRONMENT == "dev":
        with open("responses.txt", "w") as f:
            f.write("\n".join(["\nResponse nr " + str(i) + ": " + response + '\n' for i, response in enumerate(responses)]))
    
    return responses[-1]
