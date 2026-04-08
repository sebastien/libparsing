// ----------------------------------------------------------------------------
// Project           : Parsing
// ----------------------------------------------------------------------------
// Author            : Sebastien Pierre              <www.github.com/sebastien>
// License           : BSD License
// ----------------------------------------------------------------------------
// Creation date     : 2026-04-07
// Last modification : 2026-04-07
// ----------------------------------------------------------------------------
//
// Pure TypeScript port of the C/Python PEG parsing library.
//
// This implementation mirrors the Python bindings API while being entirely
// self-contained with no native dependencies. It uses JavaScript's native
// RegExp (with the sticky flag) instead of PCRE and relies on JS garbage
// collection instead of a C arena allocator.

// =============================================================================
//
// CONSTANTS
//
// =============================================================================

export const VERSION = "0.9.3";

// -- Feature flags -----------------------------------------------------------
// The TypeScript port uses native JS RegExp (always available) and JS GC
// (always available), so both feature flags are always true.

export const HAS_PCRE = true;
export const HAS_GC = true;

// -- Match / Iterator status codes -------------------------------------------

export const STATUS_INIT = "-";
export const STATUS_PROCESSING = "~";
export const STATUS_MATCHED = "M";
export const STATUS_SUCCESS = "S";
export const STATUS_PARTIAL = "p";
export const STATUS_FAILED = "F";
export const STATUS_INPUT_ENDED = ".";
export const STATUS_ENDED = "E";

// -- Element type codes ------------------------------------------------------

export const TYPE_ELEMENT = "E";
export const TYPE_WORD = "W";
export const TYPE_TOKEN = "T";
export const TYPE_GROUP = "G";
export const TYPE_RULE = "R";
export const TYPE_CONDITION = "c";
export const TYPE_PROCEDURE = "p";
export const TYPE_REFERENCE = "#";

// -- Cardinality codes -------------------------------------------------------

export const CARDINALITY_ONE = "1";
export const CARDINALITY_OPTIONAL = "?";
export const CARDINALITY_MANY = "+";
export const CARDINALITY_MANY_OPTIONAL = "*";
export const CARDINALITY_NOT_EMPTY = "=";

// -- ID constants ------------------------------------------------------------

export const ID_UNBOUND = -10;
export const ID_BINDING = -1;

// -- Flags -------------------------------------------------------------------

export const FLAG_SKIPPING = 0x1;

// =============================================================================
//
// TYPES & INTERFACES
//
// =============================================================================

/** Data carried by a Token match: the regex capture groups. */
export interface TokenMatchData {
    groups: string[];
    input: string;
    index: number;
}

/** A custom recognizer function for a Token, bypassing RegExp.
 *  Returns `{length, groups?}` on success or `null` on failure.
 *  `input` is the full input string; `offset` is where to start matching. */
export type CustomRecognizer = (
    input: string,
    offset: number
) => { length: number; groups?: string[] } | null;

export type ProcedureCallback = (
    element: ParsingElement,
    context: ParsingContext
) => void;
export type ConditionCallback = (
    element: ParsingElement,
    context: ParsingContext
) => boolean;
export type ProcessorHandler = (
    match: Match,
    processor: Processor
) => unknown;

// =============================================================================
//
// UNMATCHED SENTINEL
//
// =============================================================================

/** Sentinel object used to distinguish "optional slot did not match" from
 *  "slot matched but the handler returned `null`".  Handlers should test
 *  `value !== UNMATCHED` instead of `value !== null`. */
export const UNMATCHED: unique symbol = Symbol("UNMATCHED");

// =============================================================================
//
// ELEMENT (base interface)
//
// =============================================================================

export interface Element {
    type: string;
    id: number;
    name: string | null;
}

// =============================================================================
//
// MATCH
//
// =============================================================================

export class Match {
    status: string;
    offset: number;
    length: number;
    line: number;
    element: Element;
    data: TokenMatchData | null;
    next: Match | null;
    children: Match | null;
    parent: Match | null;
    result: unknown;

    // -- Singleton FAILURE ---------------------------------------------------

    private static _failure: Match | null = null;

    static get FAILURE(): Match {
        if (!Match._failure) {
            const f = new Match();
            f.status = STATUS_FAILED;
            f.element = { type: TYPE_ELEMENT, id: -1, name: null };
            Match._failure = f;
        }
        return Match._failure;
    }

    // -- Factories -----------------------------------------------------------

    static success(
        length: number,
        element: Element,
        offset: number,
        line: number
    ): Match {
        const m = new Match();
        m.status = STATUS_MATCHED;
        m.length = length;
        m.element = element;
        m.offset = offset;
        m.line = line;
        return m;
    }

    static fail(): Match {
        return Match.FAILURE;
    }

    // -- Constructor ---------------------------------------------------------

    constructor() {
        this.status = STATUS_INIT;
        this.offset = 0;
        this.length = 0;
        this.line = 0;
        this.element = null!; // set by factory or caller
        this.data = null;
        this.next = null;
        this.children = null;
        this.parent = null;
        this.result = null;
    }

    // -- Status helpers ------------------------------------------------------

    get isSuccess(): boolean {
        return (
            this.status === STATUS_MATCHED ||
            this.status === STATUS_SUCCESS ||
            this.status === STATUS_PARTIAL
        );
    }

    get isFailed(): boolean {
        return this.status === STATUS_FAILED;
    }

    // -- Navigation ----------------------------------------------------------

    get hasNext(): boolean {
        return this.next !== null;
    }

    get hasChildren(): boolean {
        return this.children !== null;
    }

    get firstChild(): Match | null {
        return this.children;
    }

    get endOffset(): number {
        return this.offset + this.length;
    }

    // -- Element introspection -----------------------------------------------

    /** Returns the *parsing element* type (resolving through references). */
    getType(): string {
        if (this.element && this.element.type === TYPE_REFERENCE) {
            return (this.element as Reference).element.type;
        }
        return this.element ? this.element.type : TYPE_ELEMENT;
    }

    /** Returns the name, preferring the reference name over the element name. */
    getName(): string | null {
        if (this.element && this.element.type === TYPE_REFERENCE) {
            const ref = this.element as Reference;
            return ref.name || (ref.element ? ref.element.name : null);
        }
        return this.element ? this.element.name : null;
    }

    /** Returns the parsing element (resolving through references). */
    getParsingElement(): ParsingElement | null {
        if (this.element && this.element.type === TYPE_REFERENCE) {
            return (this.element as Reference).element;
        }
        return this.element as ParsingElement;
    }

    /** Returns the element ID (resolving through references). */
    getElementID(): number {
        const pe = this.getParsingElement();
        return pe ? pe.id : (this.element ? this.element.id : -1);
    }

    // -- Convenience aliases matching the Python API -------------------------

    get type(): string {
        return this.getType();
    }

    get name(): string | null {
        return this.getName();
    }

    get id(): number {
        return this.getElementID();
    }

    get range(): [number, number] {
        return [this.offset, this.offset + this.length];
    }

    // -- Value extraction ----------------------------------------------------

    /** Returns the matched text value for leaf elements (Word, Token). */
    get value(): string | null {
        const t = this.getType();
        if (t === TYPE_WORD) {
            const pe = this.getParsingElement();
            return pe ? (pe as Word).word : null;
        }
        if (t === TYPE_TOKEN) {
            if (this.data && this.data.groups.length > 0) {
                return this.data.groups[0];
            }
            return null;
        }
        // For references, recurse into children
        if (this.element && this.element.type === TYPE_REFERENCE) {
            if (this.hasChildren) {
                return this.children!.value;
            }
        }
        return null;
    }

    /** Returns capture groups.
     *  - For a Token: the regex capture groups array.
     *  - For a Word: `[wordValue]`.
     *  - For composites: recursively collects from children. */
    group(index: number = 0): string[] {
        const t = this.getType();
        if (t === TYPE_TOKEN) {
            return this.data ? [...this.data.groups] : [];
        }
        if (t === TYPE_WORD) {
            const v = this.value;
            return v !== null ? [v] : [];
        }
        if (t === TYPE_REFERENCE || t === TYPE_RULE || t === TYPE_GROUP) {
            const result: string[] = [];
            for (const child of this) {
                result.push(...child.group());
            }
            return result;
        }
        return [];
    }

    // -- Children helpers ----------------------------------------------------

    countChildren(): number {
        let count = 0;
        let child = this.children;
        while (child) {
            count++;
            child = child.next;
        }
        return count;
    }

    /** Get a child by numeric index or by named-reference key. */
    get(indexOrKey?: number | string): Match | Record<string, Match> | null {
        if (indexOrKey === undefined) {
            // Return dict of named children
            const dict: Record<string, Match> = {};
            for (const child of this) {
                const n = child.getName();
                if (n) dict[n] = child;
            }
            return dict;
        }
        if (typeof indexOrKey === "number") {
            let idx = indexOrKey;
            if (idx < 0) idx = this.countChildren() + idx;
            let i = 0;
            let child = this.children;
            while (child) {
                if (i === idx) return child;
                child = child.next;
                i++;
            }
            return null;
        }
        // String key: find by name
        let child = this.children;
        while (child) {
            if (child.getName() === indexOrKey) return child;
            child = child.next;
        }
        return null;
    }

    /** Returns named children. */
    slots(): Match[] {
        const result: Match[] = [];
        for (const child of this) {
            if (child.getName()) result.push(child);
        }
        return result;
    }

    indexForKey(name: string): number {
        let i = 0;
        for (const child of this) {
            if (child.getName() === name) return i;
            i++;
        }
        return -1;
    }

    // -- Iteration -----------------------------------------------------------

    *[Symbol.iterator](): Iterator<Match> {
        let child = this.children;
        while (child) {
            yield child;
            child = child.next;
        }
    }

    // -- Counting ------------------------------------------------------------

    /** Counts this match plus all descendants. */
    countAll(): number {
        let count = 1;
        for (const child of this) {
            count += child.countAll();
        }
        let n = this.next;
        while (n) {
            count += n.countAll();
            n = n.next;
        }
        return count;
    }

    // -- Extract matched text from input -------------------------------------

    /** Returns the matched substring from the given input. */
    textFrom(input: string): string {
        return input.slice(this.offset, this.offset + this.length);
    }

    // -- Serialisation -------------------------------------------------------

    toJSON(): string {
        return JSON.stringify(this._toJSONObj(), null, 2);
    }

    _toJSONObj(): Record<string, unknown> {
        const obj: Record<string, unknown> = {
            type: this.getType(),
            name: this.getName(),
            id: this.getElementID(),
            offset: this.offset,
            length: this.length,
            line: this.line,
            status: this.status,
        };
        const v = this.value;
        if (v !== null) {
            obj.value = v;
        }
        if (this.hasChildren) {
            const children: Record<string, unknown>[] = [];
            for (const child of this) {
                children.push(child._toJSONObj());
            }
            obj.children = children;
        }
        return obj;
    }

    toXML(): string {
        const parts: string[] = [];
        this._writeXML(parts, 0);
        return parts.join("");
    }

    private _writeXML(parts: string[], depth: number): void {
        const indent = "  ".repeat(depth);
        const tag = this.getName() || this.getType();
        parts.push(`${indent}<${tag}`);
        parts.push(` offset="${this.offset}"`);
        parts.push(` length="${this.length}"`);
        parts.push(` line="${this.line}"`);
        const v = this.value;
        if (v !== null) {
            parts.push(` value="${_xmlEscape(v)}"`);
        }
        if (this.hasChildren) {
            parts.push(">\n");
            for (const child of this) {
                child._writeXML(parts, depth + 1);
            }
            parts.push(`${indent}</${tag}>\n`);
        } else {
            parts.push("/>\n");
        }
    }

    toString(): string {
        return `<Match ${this.getType()}:${this.getElementID()}@${this.getName() || "_"} ${this.offset}-${this.endOffset}>`;
    }
}

// =============================================================================
//
// REFERENCE
//
// =============================================================================

export class Reference implements Element {
    readonly type: string = TYPE_REFERENCE;
    id: number;
    name: string | null;
    cardinality: string;
    element: ParsingElement;
    next: Reference | null;

    constructor(element: ParsingElement) {
        this.id = ID_UNBOUND;
        this.name = null;
        this.cardinality = CARDINALITY_ONE;
        this.element = element;
        this.next = null;
    }

    /** Ensures the value is a Reference.  If a ParsingElement is given, it is
     *  wrapped in a new ONE-cardinality Reference. */
    static fromElement(elementOrRef: ParsingElement | Reference): Reference {
        if (elementOrRef instanceof Reference) {
            return elementOrRef;
        }
        return new Reference(elementOrRef);
    }

    // -- Cardinality setters (fluent) ----------------------------------------

    _as(name: string): this {
        this.name = name;
        return this;
    }

    one(): this {
        this.cardinality = CARDINALITY_ONE;
        return this;
    }

    optional(): this {
        this.cardinality = CARDINALITY_OPTIONAL;
        return this;
    }

    zeroOrMore(): this {
        this.cardinality = CARDINALITY_MANY_OPTIONAL;
        return this;
    }

    oneOrMore(): this {
        this.cardinality = CARDINALITY_MANY;
        return this;
    }

    notEmpty(): this {
        this.cardinality = CARDINALITY_NOT_EMPTY;
        return this;
    }

    // -- Cardinality queries -------------------------------------------------

    isOne(): boolean {
        return this.cardinality === CARDINALITY_ONE;
    }

    isOptional(): boolean {
        return this.cardinality === CARDINALITY_OPTIONAL;
    }

    isZeroOrMore(): boolean {
        return this.cardinality === CARDINALITY_MANY_OPTIONAL;
    }

    isOneOrMore(): boolean {
        return this.cardinality === CARDINALITY_MANY;
    }

    isMany(): boolean {
        return this.isZeroOrMore() || this.isOneOrMore();
    }

    isNotEmpty(): boolean {
        return this.cardinality === CARDINALITY_NOT_EMPTY;
    }

    isReference(): boolean {
        return true;
    }

    // -- Recognition (handles cardinality) -----------------------------------

    recognize(context: ParsingContext): Match {
        // This mirrors the C Reference_recognize:  a single loop that handles
        // all cardinalities.  On each iteration:
        //   1. Try to match the wrapped element.
        //   2. On success – accumulate the match; for ONE/OPTIONAL stop after 1.
        //   3. On failure – try to skip (whitespace/comments) then retry once;
        //      if skip didn't advance, break out.
        // After the loop the backtrack position is reset to the end of the
        // last successful match so that trailing skip doesn't eat useful input.

        const element = this.element;
        const card = this.cardinality;

        const startOffset = context.offset;
        const startLine = context.line;

        let head: Match | null = null;
        let tail: Match | null = null;
        let count = 0;
        // Track the position at the end of the last successful match so we
        // can backtrack trailing skip.
        let matchEndOffset = startOffset;
        let matchEndLine = startLine;

        let currentOffset = startOffset;

        while (context.offset < context.input.length ||
               element.type === TYPE_PROCEDURE ||
               element.type === TYPE_CONDITION) {

            const iterOffset = context.offset;
            const iterLine = context.line;
            let m = element.recognize(context);

            if (m.isSuccess) {
                matchEndOffset = context.offset;
                matchEndLine = context.line;

                if (count === 0) {
                    head = m;
                    tail = m;
                    if (
                        m.length === 0 ||
                        card === CARDINALITY_ONE ||
                        card === CARDINALITY_OPTIONAL
                    ) {
                        count++;
                        break;
                    }
                } else {
                    tail!.next = m;
                    tail = m;
                    if (m.length === 0) {
                        count++;
                        break;
                    }
                }
                count++;
            } else {
                // Match failed – try to skip and retry once.
                if (
                    context.grammar.skip &&
                    !(context.flags & FLAG_SKIPPING)
                ) {
                    const preSkip = context.offset;
                    context.applySkip();
                    if (context.offset > preSkip) {
                        // Skipped something – retry the element
                        continue;
                    }
                }
                // No skip or skip didn't advance → stop
                break;
            }

            // Guard against infinite loop (no progress)
            if (context.offset === currentOffset) {
                break;
            }
            currentOffset = context.offset;
        }

        // Backtrack to the end of the last successful match so trailing skip
        // doesn't consume input that a subsequent rule might need.
        if (context.offset !== matchEndOffset) {
            context.offset = matchEndOffset;
            context.line = matchEndLine;
        }

        // Determine success based on cardinality
        const isSuccess =
            count > 0
                ? true
                : card === CARDINALITY_OPTIONAL ||
                  card === CARDINALITY_MANY_OPTIONAL;

        if (isSuccess) {
            const length = matchEndOffset - startOffset;
            const rm = Match.success(length, this, startOffset, startLine);
            rm.children = head;
            let c = head;
            while (c) {
                c.parent = rm;
                c = c.next;
            }
            return rm;
        } else {
            // Failure – restore offset
            context.offset = startOffset;
            context.line = startLine;
            return Match.fail();
        }
    }

    toString(): string {
        return `<Reference ${this.id}@${this.name || "_"}\u2192${this.element?.name || this.element?.type}>`;
    }
}

// =============================================================================
//
// PARSING ELEMENT (abstract base)
//
// =============================================================================

export abstract class ParsingElement implements Element {
    abstract readonly type: string;
    id: number;
    name: string | null;
    children: Reference | null;

    constructor() {
        this.id = ID_UNBOUND;
        this.name = null;
        this.children = null;
    }

    /** Core recognition method — implemented by each concrete element. */
    abstract recognize(context: ParsingContext): Match;

    // -- Child management ----------------------------------------------------

    add(...children: (ParsingElement | Reference)[]): this {
        for (const child of children) {
            const ref = Reference.fromElement(child);
            if (this.children === null) {
                this.children = ref;
            } else {
                let tail = this.children;
                while (tail.next !== null) tail = tail.next;
                tail.next = ref;
            }
        }
        return this;
    }

    clear(): this {
        this.children = null;
        return this;
    }

    set(...children: (ParsingElement | Reference)[]): this {
        this.clear();
        return this.add(...children);
    }

    replace(index: number, child: ParsingElement | Reference): this {
        const ref = Reference.fromElement(child);
        const refs = this._childRefs();
        if (index >= 0 && index < refs.length) {
            ref.next = null;
            refs[index] = ref;
            this._rebuildChildren(refs);
        }
        return this;
    }

    insert(index: number, child: ParsingElement | Reference): this {
        const ref = Reference.fromElement(child);
        const refs = this._childRefs();
        ref.next = null;
        refs.splice(index, 0, ref);
        this._rebuildChildren(refs);
        return this;
    }

    prepend(...children: (ParsingElement | Reference)[]): this {
        const existing = this._childRefs();
        this.children = null;
        this.add(...children);
        for (const r of existing) {
            r.next = null;
            this.add(r);
        }
        return this;
    }

    // -- Reference convenience helpers (fluent) ------------------------------

    /** Creates a named reference to this element. */
    _as(name: string): Reference {
        return new Reference(this)._as(name);
    }

    optional(): Reference {
        return new Reference(this).optional();
    }

    zeroOrMore(): Reference {
        return new Reference(this).zeroOrMore();
    }

    oneOrMore(): Reference {
        return new Reference(this).oneOrMore();
    }

    notEmpty(): Reference {
        return new Reference(this).notEmpty();
    }

    // -- Introspection -------------------------------------------------------

    /** Returns the names of named child references. */
    slots(): string[] {
        const result: string[] = [];
        let child = this.children;
        while (child) {
            if (child.name) result.push(child.name);
            child = child.next;
        }
        return result;
    }

    /** Returns the child index for the given named reference, or -1. */
    indexForKey(name: string): number {
        let index = 0;
        let child = this.children;
        while (child) {
            if (child.name === name) return index;
            index++;
            child = child.next;
        }
        return -1;
    }

    isReference(): boolean {
        return false;
    }

    // -- Private helpers -----------------------------------------------------

    private _childRefs(): Reference[] {
        const refs: Reference[] = [];
        let c = this.children;
        while (c) {
            refs.push(c);
            c = c.next;
        }
        return refs;
    }

    private _rebuildChildren(refs: Reference[]): void {
        this.children = null;
        for (let i = 0; i < refs.length; i++) {
            refs[i].next = i + 1 < refs.length ? refs[i + 1] : null;
        }
        if (refs.length > 0) this.children = refs[0];
    }

    toString(): string {
        return `<${this.constructor.name} ${this.type}@${this.name || "_"}#${this.id}>`;
    }
}

// =============================================================================
//
// WORD
//
// =============================================================================

/** Recognises a static literal string at the current iterator location. */
export class Word extends ParsingElement {
    readonly type: string = TYPE_WORD;
    readonly word: string;
    private readonly _length: number;

    constructor(word: string) {
        super();
        this.word = word;
        this._length = word.length;
    }

    recognize(context: ParsingContext): Match {
        const offset = context.offset;
        const remaining = context.input.length - offset;

        if (remaining < this._length) {
            return Match.fail();
        }

        // Fast path: compare characters directly
        for (let i = 0; i < this._length; i++) {
            if (context.input.charCodeAt(offset + i) !== this.word.charCodeAt(i)) {
                return Match.fail();
            }
        }

        const m = Match.success(this._length, this, offset, context.line);
        context.offset += this._length;
        return m;
    }
}

// =============================================================================
//
// TOKEN
//
// =============================================================================

/** Recognises a regular-expression pattern (or a custom recogniser) at the
 *  current iterator location. */
export class Token extends ParsingElement {
    readonly type: string = TYPE_TOKEN;
    readonly expr: string;
    private _regexp: RegExp;
    private _customRecognize: CustomRecognizer | null;

    constructor(expr: string) {
        super();
        this.expr = expr;
        this._customRecognize = null;
        // The sticky flag (y) anchors the match at lastIndex, which is equivalent
        // to PCRE's PCRE_ANCHORED.
        this._regexp = new RegExp(expr, "y");
    }

    /** Sets a custom recogniser function, bypassing RegExp. */
    setCustomRecognize(fn: CustomRecognizer): this {
        this._customRecognize = fn;
        return this;
    }

    /** Use the built-in hand-coded JSON string recogniser. */
    setJSONStringRecognizer(): this {
        this._customRecognize = Recognizers.jsonString;
        return this;
    }

    /** Use the built-in hand-coded JSON number recogniser. */
    setJSONNumberRecognizer(): this {
        this._customRecognize = Recognizers.jsonNumber;
        return this;
    }

    recognize(context: ParsingContext): Match {
        const input = context.input;
        const offset = context.offset;

        if (this._customRecognize) {
            return this._recognizeCustom(input, offset, context);
        }
        return this._recognizeRegex(input, offset, context);
    }

    private _recognizeCustom(
        input: string,
        offset: number,
        context: ParsingContext
    ): Match {
        const result = this._customRecognize!(input, offset);
        if (result && result.length > 0) {
            const m = Match.success(result.length, this, offset, context.line);
            const groups = result.groups
                ? result.groups
                : [input.slice(offset, offset + result.length)];
            m.data = { groups, input, index: offset };

            // Update line counter
            context.line += _countNewlines(input, offset, offset + result.length);
            context.offset += result.length;
            return m;
        }
        return Match.fail();
    }

    private _recognizeRegex(
        input: string,
        offset: number,
        context: ParsingContext
    ): Match {
        this._regexp.lastIndex = offset;
        const result = this._regexp.exec(input);

        if (result && result.index === offset) {
            const matched = result[0];
            const m = Match.success(matched.length, this, offset, context.line);

            // Build groups array from regex result
            const groups: string[] = [];
            for (let i = 0; i < result.length; i++) {
                groups.push(result[i] !== undefined ? result[i] : "");
            }
            m.data = { groups, input, index: offset };

            // Update line counter
            context.line += _countNewlines(input, offset, offset + matched.length);
            context.offset += matched.length;
            return m;
        }

        return Match.fail();
    }
}

// =============================================================================
//
// GROUP (ordered choice / alternation)
//
// =============================================================================

/** Returns the first matching child's match (PEG ordered choice). */
export class Group extends ParsingElement {
    readonly type: string = TYPE_GROUP;

    constructor(...children: (ParsingElement | Reference)[]) {
        super();
        if (children.length > 0) this.add(...children);
    }

    recognize(context: ParsingContext): Match {
        // Memoisation lookup
        if (!context.noMemo && this.id >= 0) {
            const cached = context.memoGet(this.id, context.offset);
            if (cached) return cached;
        }

        const savedOffset = context.offset;
        const savedLine = context.line;

        // Note: we don't skip in groups; that's the business of references
        // (as per the C implementation).
        let child = this.children;
        while (child) {
            const m = child.recognize(context);
            if (m.isSuccess) {
                // Wrap in a Group-level match (mirrors C Group_recognize which
                // creates Match_Success(length, this, context) with children = match).
                const result = Match.success(
                    m.length,
                    this,
                    savedOffset,
                    savedLine
                );
                result.children = m;
                m.parent = result;

                if (!context.noMemo && this.id >= 0) {
                    context.memoSet(
                        this.id,
                        savedOffset,
                        result,
                        context.offset,
                        context.line
                    );
                }
                return result;
            }
            // Backtrack
            context.offset = savedOffset;
            context.line = savedLine;
            child = child.next;
        }

        if (!context.noMemo && this.id >= 0) {
            context.memoSet(this.id, savedOffset, null, savedOffset, savedLine);
        }
        return Match.fail();
    }
}

// =============================================================================
//
// RULE (sequence)
//
// =============================================================================

/** All children must match in sequence (PEG sequence). */
export class Rule extends ParsingElement {
    readonly type: string = TYPE_RULE;

    constructor(...children: (ParsingElement | Reference)[]) {
        super();
        if (children.length > 0) this.add(...children);
    }

    recognize(context: ParsingContext): Match {
        // Memoisation lookup
        if (!context.noMemo && this.id >= 0) {
            const cached = context.memoGet(this.id, context.offset);
            if (cached) return cached;
        }

        const savedOffset = context.offset;
        const savedLine = context.line;

        // Push variable scope
        context.push();

        let head: Match | null = null;
        let tail: Match | null = null;
        let failed = false;

        let child = this.children;
        while (child) {
            let m = child.recognize(context);

            // If the match failed, try to skip (whitespace/comments) and retry.
            // This mirrors the C Rule_recognize behaviour where skip is applied
            // on failure-then-retry, which also handles leading whitespace
            // before the very first child.
            if (
                !m.isSuccess &&
                context.grammar.skip &&
                !(context.flags & FLAG_SKIPPING)
            ) {
                const preSkipOffset = context.offset;
                context.applySkip();
                if (context.offset > preSkipOffset) {
                    // Skipped something — retry the child
                    m = child.recognize(context);
                }
            }

            if (!m.isSuccess) {
                failed = true;
                break;
            }

            if (head === null) {
                head = m;
                tail = m;
            } else {
                tail!.next = m;
                tail = m;
            }

            child = child.next;
        }

        context.pop();

        if (failed) {
            context.offset = savedOffset;
            context.line = savedLine;
            if (!context.noMemo && this.id >= 0) {
                context.memoSet(
                    this.id,
                    savedOffset,
                    null,
                    savedOffset,
                    savedLine
                );
            }
            return Match.fail();
        }

        // Build aggregate match
        const totalLength = context.offset - savedOffset;
        const rm = Match.success(totalLength, this, savedOffset, savedLine);
        rm.children = head;

        // Set parent pointers
        let c = head;
        while (c) {
            c.parent = rm;
            c = c.next;
        }

        if (!context.noMemo && this.id >= 0) {
            context.memoSet(
                this.id,
                savedOffset,
                rm,
                context.offset,
                context.line
            );
        }
        return rm;
    }
}

// =============================================================================
//
// PROCEDURE
//
// =============================================================================

/** Always succeeds with zero length; runs a side-effect callback. */
export class Procedure extends ParsingElement {
    readonly type: string = TYPE_PROCEDURE;
    private _callback: ProcedureCallback;

    constructor(callback: ProcedureCallback) {
        super();
        this._callback = callback;
    }

    recognize(context: ParsingContext): Match {
        this._callback(this, context);
        return Match.success(0, this, context.offset, context.line);
    }
}

// =============================================================================
//
// CONDITION
//
// =============================================================================

/** Succeeds (zero length) if the callback returns true, fails otherwise. */
export class Condition extends ParsingElement {
    readonly type: string = TYPE_CONDITION;
    private _callback: ConditionCallback;

    constructor(callback: ConditionCallback) {
        super();
        this._callback = callback;
    }

    recognize(context: ParsingContext): Match {
        if (this._callback(this, context)) {
            return Match.success(0, this, context.offset, context.line);
        }
        return Match.fail();
    }
}

// =============================================================================
//
// VARIABLE STACK
//
// =============================================================================

class VariableStack {
    private _stack: Map<string, unknown>[];

    constructor() {
        this._stack = [new Map()];
    }

    push(): void {
        this._stack.push(new Map());
    }

    pop(): void {
        if (this._stack.length > 1) {
            this._stack.pop();
        }
    }

    get(key: string): unknown {
        // Search from top of stack downwards
        for (let i = this._stack.length - 1; i >= 0; i--) {
            if (this._stack[i].has(key)) {
                return this._stack[i].get(key);
            }
        }
        return undefined;
    }

    set(key: string, value: unknown): void {
        this._stack[this._stack.length - 1].set(key, value);
    }

    count(): number {
        let n = 0;
        for (const frame of this._stack) n += frame.size;
        return n;
    }
}

// =============================================================================
//
// MEMO ENTRY
//
// =============================================================================

interface MemoEntry {
    match: Match | null;
    endOffset: number;
    endLine: number;
}

// =============================================================================
//
// PARSING STATS
//
// =============================================================================

export class ParsingStats {
    bytesRead: number = 0;
    parseTime: number = 0;
    symbolsCount: number = 0;
    successBySymbol: number[] = [];
    failureBySymbol: number[] = [];
    failureOffset: number = 0;
    matchOffset: number = 0;
    matchLength: number = 0;
    failureElement: Element | null = null;

    setSymbolsCount(count: number): void {
        this.symbolsCount = count;
        this.successBySymbol = new Array(count).fill(0);
        this.failureBySymbol = new Array(count).fill(0);
    }

    totalSuccess(): number {
        let sum = 0;
        for (let i = 0; i < this.symbolsCount; i++) sum += this.successBySymbol[i];
        return sum;
    }

    totalFailures(): number {
        let sum = 0;
        for (let i = 0; i < this.symbolsCount; i++) sum += this.failureBySymbol[i];
        return sum;
    }

    report(grammar?: Grammar): string {
        const lines: string[] = [];
        const br = this.bytesRead;
        const pt = this.parseTime;
        const ts = this.totalSuccess();
        const tf = this.totalFailures();
        lines.push(`Bytes read :  ${br}`);
        lines.push(`Parse time :  ${pt}s`);
        lines.push(`Throughput :  ${(br / 1024 / 1024 / pt).toFixed(2)}Mb/s`);
        lines.push("-".repeat(80));
        lines.push(`Successes  :  ${ts}`);
        lines.push(`Failures   :  ${tf}`);
        lines.push(`Throughput :  ${((ts + tf) / pt).toFixed(0)}op/s`);
        lines.push("-".repeat(80));
        if (grammar) {
            for (let i = 0; i < this.symbolsCount; i++) {
                const s = this.successBySymbol[i];
                const f = this.failureBySymbol[i];
                if (s === 0 && f === 0) continue;
                let name = "";
                try {
                    const sym = grammar.symbol(i);
                    name = sym.name || sym.type;
                } catch {
                    /* empty */
                }
                lines.push(
                    `${String(i).padStart(9)} ${name.padEnd(31)} ${String(s).padStart(14)} ${String(f).padStart(14)}`
                );
            }
        }
        return lines.join("\n");
    }
}

// =============================================================================
//
// PARSING CONTEXT
//
// =============================================================================

export class ParsingContext {
    grammar: Grammar;
    input: string;
    offset: number;
    line: number;
    variables: VariableStack;
    stats: ParsingStats;
    lastMatchOffset: number;
    lastMatchLength: number;
    lastMatchElementID: number;
    flags: number;
    depth: number;
    noMemo: boolean;

    private _memoTable: Map<string, MemoEntry>;
    private _startTime: number;

    constructor(grammar: Grammar, input: string) {
        this.grammar = grammar;
        this.input = input;
        this.offset = 0;
        this.line = 0;
        this.variables = new VariableStack();
        this.stats = new ParsingStats();
        this.lastMatchOffset = 0;
        this.lastMatchLength = 0;
        this.lastMatchElementID = -1;
        this.flags = 0;
        this.depth = 0;
        this.noMemo = grammar.noMemo;
        this._memoTable = new Map();
        this._startTime = _now();
    }

    // -- Input access --------------------------------------------------------

    charAt(offset: number): string {
        return offset >= 0 && offset < this.input.length
            ? this.input[offset]
            : "";
    }

    remaining(): number {
        return this.input.length - this.offset;
    }

    text(): string {
        return this.input;
    }

    // -- Variable scoping ----------------------------------------------------

    push(): void {
        this.variables.push();
        this.depth++;
    }

    pop(): void {
        this.variables.pop();
        this.depth--;
    }

    getVar(key: string): unknown {
        return this.variables.get(key);
    }

    setVar(key: string, value: unknown): void {
        this.variables.set(key, value);
    }

    getVariableCount(): number {
        return this.variables.count();
    }

    // -- Packrat memoisation -------------------------------------------------

    /** Returns a cached match for `(elementId, offset)` or `null` on miss.
     *  A cache hit for a failure returns `Match.FAILURE`. */
    memoGet(elementId: number, offset: number): Match | null {
        if (this.noMemo) return null;
        const key = `${elementId}:${offset}`;
        const entry = this._memoTable.get(key);
        if (!entry) return null;
        if (entry.match === null) {
            // Cached failure
            return Match.FAILURE;
        }
        // Restore context to end position
        this.offset = entry.endOffset;
        this.line = entry.endLine;
        return entry.match;
    }

    /** Stores a match result in the memo table.  Pass `null` for failures. */
    memoSet(
        elementId: number,
        offset: number,
        match: Match | null,
        endOffset: number,
        endLine: number
    ): void {
        if (this.noMemo) return;
        const key = `${elementId}:${offset}`;
        this._memoTable.set(key, { match, endOffset, endLine });
    }

    // -- Skip ----------------------------------------------------------------

    /** Applies the grammar's skip element once (e.g. whitespace). */
    applySkip(): void {
        if (!this.grammar.skip) return;
        if (this.flags & FLAG_SKIPPING) return;

        this.flags |= FLAG_SKIPPING;

        if (this.grammar.skipWhitespace) {
            // Fast hand-coded ASCII whitespace skip
            const inp = this.input;
            let i = this.offset;
            while (i < inp.length) {
                const ch = inp.charCodeAt(i);
                if (ch === 32 || ch === 9 || ch === 13) {
                    // space, tab, CR
                    i++;
                } else if (ch === 10) {
                    // LF
                    this.line++;
                    i++;
                } else {
                    break;
                }
            }
            this.offset = i;
        } else {
            const savedOffset = this.offset;
            const savedLine = this.line;
            const m = this.grammar.skip.recognize(this);
            if (!m.isSuccess) {
                this.offset = savedOffset;
                this.line = savedLine;
            }
        }

        this.flags &= ~FLAG_SKIPPING;
    }

    // -- Stats ---------------------------------------------------------------

    registerMatch(element: Element, match: Match): void {
        if (match.isSuccess) {
            const end = match.offset + match.length;
            if (end > this.lastMatchOffset) {
                this.lastMatchOffset = end;
                this.lastMatchLength = match.length;
                this.lastMatchElementID = element.id;
            }
        } else {
            if (this.offset > this.stats.failureOffset) {
                this.stats.failureOffset = this.offset;
                this.stats.failureElement = element;
            }
        }
        if (element.id >= 0 && element.id < this.stats.symbolsCount) {
            if (match.isSuccess) {
                this.stats.successBySymbol[element.id]++;
            } else {
                this.stats.failureBySymbol[element.id]++;
            }
        }
    }

    get parseTime(): number {
        return (_now() - this._startTime) / 1000;
    }
}

// =============================================================================
//
// SYMBOLS
//
// =============================================================================

/** Dict-like container for named grammar symbols, supporting attribute-style
 *  access (e.g. `s.NUMBER`). */
export class Symbols {
    [key: string]: ParsingElement;
}

// =============================================================================
//
// GRAMMAR
//
// =============================================================================

export class Grammar {
    axiom: ParsingElement | null;
    skip: ParsingElement | null;
    isVerbose: boolean;
    noMemo: boolean;
    skipWhitespace: boolean;
    symbols: Symbols;

    private _prepared: boolean;
    private _anonymous: ParsingElement[];
    private _elements: Element[];
    private _elementCount: number;

    constructor(options?: {
        name?: string;
        isVerbose?: boolean;
        axiom?: ParsingElement;
        skip?: ParsingElement;
    }) {
        this.axiom = null;
        this.skip = null;
        this.isVerbose = false;
        this.noMemo = false;
        this.skipWhitespace = false;
        this.symbols = new Symbols();
        this._prepared = false;
        this._anonymous = [];
        this._elements = [];
        this._elementCount = 0;

        if (options) {
            if (options.isVerbose !== undefined) this.isVerbose = options.isVerbose;
            if (options.axiom) this.axiom = options.axiom;
            if (options.skip) this.skip = options.skip;
        }
    }

    // -----------------------------------------------------------------------
    // Factory methods
    // -----------------------------------------------------------------------

    word(name: string, pattern: string): Word {
        this._prepared = false;
        const w = new Word(pattern);
        w.name = name;
        this.symbols[name] = w;
        return w;
    }

    aword(pattern: string): Word {
        this._prepared = false;
        const w = new Word(pattern);
        this._anonymous.push(w);
        return w;
    }

    token(name: string, pattern: string): Token {
        this._prepared = false;
        const t = new Token(pattern);
        t.name = name;
        this.symbols[name] = t;
        return t;
    }

    atoken(pattern: string): Token {
        this._prepared = false;
        const t = new Token(pattern);
        this._anonymous.push(t);
        return t;
    }

    rule(name: string, ...children: (ParsingElement | Reference)[]): Rule {
        this._prepared = false;
        const r = new Rule(...children);
        r.name = name;
        this.symbols[name] = r;
        return r;
    }

    arule(...children: (ParsingElement | Reference)[]): Rule {
        this._prepared = false;
        const r = new Rule(...children);
        this._anonymous.push(r);
        return r;
    }

    group(name: string, ...children: (ParsingElement | Reference)[]): Group {
        this._prepared = false;
        const g = new Group(...children);
        g.name = name;
        this.symbols[name] = g;
        return g;
    }

    agroup(...children: (ParsingElement | Reference)[]): Group {
        this._prepared = false;
        const g = new Group(...children);
        this._anonymous.push(g);
        return g;
    }

    procedure(name: string, callback: ProcedureCallback): Procedure {
        this._prepared = false;
        const p = new Procedure(callback);
        p.name = name;
        this.symbols[name] = p;
        return p;
    }

    aprocedure(callback: ProcedureCallback): Procedure {
        this._prepared = false;
        const p = new Procedure(callback);
        this._anonymous.push(p);
        return p;
    }

    condition(name: string, callback: ConditionCallback): Condition {
        this._prepared = false;
        const c = new Condition(callback);
        c.name = name;
        this.symbols[name] = c;
        return c;
    }

    acondition(callback: ConditionCallback): Condition {
        this._prepared = false;
        const c = new Condition(callback);
        this._anonymous.push(c);
        return c;
    }

    // -----------------------------------------------------------------------
    // Parsing
    // -----------------------------------------------------------------------

    parseString(text: string): ParsingResult {
        this._ensurePrepared();

        const context = new ParsingContext(this, text);
        context.stats.setSymbolsCount(this._elementCount);
        context.stats.bytesRead = text.length;

        if (!this.axiom) {
            throw new Error("Grammar has no axiom set");
        }

        const match = this.axiom.recognize(context);

        let status: string;
        if (match.isSuccess) {
            if (context.offset >= text.length) {
                status = STATUS_SUCCESS;
            } else {
                status = STATUS_PARTIAL;
            }
        } else {
            status = STATUS_FAILED;
        }

        context.stats.parseTime = context.parseTime;
        return new ParsingResult(match, context, status);
    }

    // -----------------------------------------------------------------------
    // Configuration
    // -----------------------------------------------------------------------

    setVerbose(value = true): this {
        this.isVerbose = value;
        return this;
    }

    setSilent(): this {
        this.isVerbose = false;
        return this;
    }

    setNoMemo(value = true): this {
        this.noMemo = value;
        return this;
    }

    setSkipWhitespace(value = true): this {
        this.skipWhitespace = value;
        return this;
    }

    // -----------------------------------------------------------------------
    // Preparation
    // -----------------------------------------------------------------------

    /** Assigns breadth-first IDs to all elements and builds the flat element
     *  table.  Called automatically before parsing. */
    prepare(): void {
        if (!this.axiom) {
            throw new Error("Grammar has no axiom set");
        }

        // Phase 1: Reset all IDs to ID_BINDING
        const visited = new Set<Element>();
        this._resetIds(this.axiom, visited);
        if (this.skip) this._resetIds(this.skip, visited);

        // Phase 2: Assign IDs breadth-first
        let nextId = 0;
        nextId = this._assignIdsBFS(this.axiom, nextId);
        if (this.skip) nextId = this._assignIdsBFS(this.skip, nextId);

        // Phase 3: Build flat element table
        this._elements = new Array(nextId).fill(null);
        this._collectElements(this.axiom);
        if (this.skip) this._collectElements(this.skip);
        this._elementCount = nextId;

        this._prepared = true;
    }

    private _resetIds(element: ParsingElement, visited: Set<Element>): void {
        if (visited.has(element)) return;
        visited.add(element);
        element.id = ID_BINDING;

        let child = element.children;
        while (child) {
            visited.add(child);
            child.id = ID_BINDING;
            if (child.element) {
                this._resetIds(child.element, visited);
            }
            child = child.next;
        }
    }

    private _assignIdsBFS(
        root: ParsingElement,
        nextId: number
    ): number {
        if (root.id !== ID_BINDING) return nextId;

        const queue: ParsingElement[] = [root];
        root.id = nextId++;

        let qi = 0;
        while (qi < queue.length) {
            const el = queue[qi++];
            let child = el.children;
            while (child) {
                // Assign ID to the reference
                child.id = nextId++;
                // Assign ID to the referenced element (if not yet assigned)
                if (child.element && child.element.id === ID_BINDING) {
                    child.element.id = nextId++;
                    queue.push(child.element);
                }
                child = child.next;
            }
        }

        return nextId;
    }

    private _collectElements(element: ParsingElement): void {
        if (element.id >= 0 && element.id < this._elements.length) {
            if (this._elements[element.id]) return; // Already collected
            this._elements[element.id] = element;
        }

        let child = element.children;
        while (child) {
            if (child.id >= 0 && child.id < this._elements.length) {
                this._elements[child.id] = child;
            }
            if (child.element) {
                this._collectElements(child.element);
            }
            child = child.next;
        }
    }

    // -----------------------------------------------------------------------
    // Introspection
    // -----------------------------------------------------------------------

    /** Returns a symbol by numeric ID or by name. */
    symbol(id: number | string): Element {
        if (typeof id === "number") {
            if (id >= 0 && id < this._elements.length && this._elements[id]) {
                return this._elements[id];
            }
            throw new Error(`Symbol ID out of range: ${id}`);
        }
        const s = this.symbols[id];
        if (!s) throw new Error(`Unknown symbol: ${id}`);
        return s;
    }

    /** Returns `[name, element]` pairs for all named symbols. */
    list(): [string, ParsingElement][] {
        const result: [string, ParsingElement][] = [];
        for (const key of Object.keys(this.symbols)) {
            if (!key.startsWith("_")) {
                result.push([key, this.symbols[key]]);
            }
        }
        return result;
    }

    /** Returns the total number of elements (after preparation). */
    symbolsCount(): number {
        return this._elementCount;
    }

    get prepared(): boolean {
        return this._prepared;
    }

    private _ensurePrepared(): void {
        if (!this._prepared) this.prepare();
    }

    toString(): string {
        return `<Grammar symbols=${Object.keys(this.symbols).length} axiom=${this.axiom?.name || "none"}>`;
    }
}

// =============================================================================
//
// PARSING RESULT
//
// =============================================================================

export class ParsingResult {
    match: Match | null;
    context: ParsingContext;
    status: string;

    constructor(match: Match | null, context: ParsingContext, status: string) {
        this.match = match && match.isSuccess ? match : null;
        this.context = context;
        this.status = status;
    }

    isSuccess(): boolean {
        return this.status === STATUS_SUCCESS || this.status === STATUS_PARTIAL;
    }

    isFailure(): boolean {
        return this.status === STATUS_FAILED;
    }

    isPartial(): boolean {
        return this.status === STATUS_PARTIAL;
    }

    isComplete(): boolean {
        return this.isSuccess() && !this.isPartial();
    }

    get line(): number {
        return this.context.line;
    }

    get offset(): number {
        return this.context.offset;
    }

    get remaining(): number {
        return this.context.remaining();
    }

    get text(): string {
        return this.context.input;
    }

    get textOffset(): number {
        return this.context.offset;
    }

    get lastMatch(): {
        offset: number;
        length: number;
        id: number;
        element: Element | null;
    } {
        const g = this.context.grammar;
        let elem: Element | null = null;
        if (this.context.lastMatchElementID >= 0) {
            try {
                elem = g.symbol(this.context.lastMatchElementID);
            } catch {
                /* empty */
            }
        }
        return {
            offset: this.context.lastMatchOffset,
            length: this.context.lastMatchLength,
            id: this.context.lastMatchElementID,
            element: elem,
        };
    }

    get lastMatchOffset(): number {
        return this.context.lastMatchOffset;
    }

    get lastMatchLength(): number {
        return this.context.lastMatchLength;
    }

    get stats(): ParsingStats {
        return this.context.stats;
    }

    /** Returns a nicely formatted description of the result. */
    describe(contextLines = 3): string {
        if (this.isSuccess()) {
            return "Parsing successful";
        }
        const s = this.context.lastMatchOffset;
        const e = s + this.context.lastMatchLength;
        const t = this.context.input;
        const lines = t.slice(0, s).split("\n");
        const lineNum = lines.length - 1;
        const charNum = lines[lines.length - 1].length;

        const lm = this.lastMatch;
        const symStr =
            lm.element && lm.element.name
                ? `, symbol ${lm.element.name}`
                : "";

        const ctx = this.getContext(s, e, contextLines, contextLines);
        const ctxStr = this._formatContext(ctx);

        return `Parsing failed at line ${lineNum} character ${charNum}, offset ${s}\u2192${e}${symStr}:${ctxStr}`;
    }

    /** Returns context lines around the given offsets. */
    getContext(
        start?: number,
        end?: number,
        before = 3,
        after = 3
    ): {
        before: string[];
        line: string;
        after: string[];
        start: number;
        end: number;
        lineBefore: string;
        lineMatch: string;
        lineAfter: string;
        lineOffset: number;
        lineLength: number;
    } {
        if (start === undefined || end === undefined) {
            start = this.context.lastMatchOffset;
            end = start + this.context.lastMatchLength;
        }
        const t = this.context.input;
        const bt = t.slice(0, start).split("\n").slice(-(before + 1));
        const at = t.slice(end).split("\n").slice(0, after + 1);
        const lineBefore = bt[bt.length - 1] || "";
        const lineMatch = t.slice(start, end);
        const lineAfter = at[0] || "";
        return {
            before: bt.slice(0, -1),
            line: lineBefore + lineMatch + lineAfter,
            after: at.slice(1),
            start,
            end,
            lineBefore,
            lineMatch,
            lineAfter,
            lineOffset: lineBefore.length,
            lineLength: Math.max(0, end - start),
        };
    }

    private _formatContext(ctx: {
        before: string[];
        line: string;
        after: string[];
        lineBefore: string;
        lineMatch: string;
        lineAfter: string;
    }): string {
        const parts: string[] = [];
        for (const l of ctx.before) {
            parts.push(`\n| ${l}`);
        }
        parts.push(`\n> ${ctx.line}`);
        parts.push(
            `\n  ${" ".repeat(ctx.lineBefore.length)}${"^".repeat(Math.max(1, ctx.lineMatch.length))}`
        );
        for (const l of ctx.after) {
            parts.push(`\n| ${l}`);
        }
        return parts.join("");
    }

    toJSON(): string {
        return this.match ? this.match.toJSON() : "null";
    }

    toXML(): string {
        return this.match ? this.match.toXML() : "";
    }

    toString(): string {
        return `<ParsingResult status=${this.status} line=${this.line} offset=${this.offset} remaining=${this.remaining}>`;
    }
}

// =============================================================================
//
// MATCH RESULT
//
// =============================================================================

/** Wraps a processed value together with the original Match that produced it. */
export class MatchResult {
    value: unknown;
    match: Match;

    constructor(value: unknown, match: Match) {
        this.value = value;
        this.match = match;
    }

    get name(): string | null {
        return this.match.getName();
    }

    get id(): number {
        return this.match.getElementID();
    }

    group(index = 0): string[] {
        return this.match.group(index);
    }

    toString(): string {
        return `<MatchResult ${this.match}=${this.value}>`;
    }
}

// =============================================================================
//
// PROCESSOR
//
// =============================================================================

/** Tree-walker that transforms a match tree by dispatching to registered
 *  handlers.  Methods named `onSymbolName` are auto-registered for the
 *  corresponding grammar symbol.
 *
 *  Strategies:
 *  - `LAZY` (default): only processes nodes when a handler requests them.
 *  - `EAGER`: processes the entire tree bottom-up. */
export class Processor {
    static readonly LAZY = 0;
    static readonly EAGER = 1;

    strategy: number;
    isStrict: boolean;
    grammar: Grammar | null;
    depth: number;

    /** Maps element ID -> handler function */
    handlerByID: Map<number, ProcessorHandler>;

    /** Maps element ID -> symbol object */
    symbolByID: Map<number, Element>;

    /** Maps symbol name -> symbol object */
    symbolByName: Map<string, ParsingElement>;

    private _defaults: Record<string, (match: Match) => unknown>;

    constructor(grammar?: Grammar, strict = true) {
        this.depth = 0;
        this.isStrict = strict;
        this.strategy = Processor.LAZY;
        this.grammar = null;
        this.handlerByID = new Map();
        this.symbolByID = new Map();
        this.symbolByName = new Map();
        this._defaults = {};

        if (grammar) {
            this.setGrammar(this.ensureGrammar(grammar));
        } else {
            this._bindHandlers();
        }
    }

    // -- Configuration -------------------------------------------------------

    /** Registers a handler for the given symbol. */
    on(symbol: ParsingElement, handler: ProcessorHandler): this {
        this.handlerByID.set(symbol.id, handler);
        return this;
    }

    asEager(): this {
        this.strategy = Processor.EAGER;
        return this;
    }

    asLazy(): this {
        this.strategy = Processor.LAZY;
        return this;
    }

    /** Override to create the grammar when none is provided. */
    createGrammar(): Grammar {
        throw new Error("createGrammar() not implemented");
    }

    ensureGrammar(grammar?: Grammar): Grammar {
        return grammar || this.createGrammar();
    }

    setGrammar(grammar: Grammar): this {
        this.grammar = grammar;
        this.grammar.prepare();

        // Build symbol maps
        this.symbolByName.clear();
        this.symbolByID.clear();
        for (const [name, sym] of this.grammar.list()) {
            this.symbolByName.set(name, sym);
            if (sym.id >= 0) {
                this.symbolByID.set(sym.id, sym);
            }
        }

        this._bindHandlers();
        return this;
    }

    // -- Handler binding (auto-discovers `onXxx` methods) --------------------

    private _bindHandlers(): void {
        const proto = Object.getPrototypeOf(this);
        const names = new Set<string>();

        // Walk the prototype chain to find all onXxx methods
        let p = proto;
        while (p && p !== Object.prototype) {
            for (const key of Object.getOwnPropertyNames(p)) {
                if (key.startsWith("on") && key.length > 2) {
                    names.add(key);
                }
            }
            p = Object.getPrototypeOf(p);
        }

        for (const key of names) {
            const symbolName = key.slice(2); // Strip "on" prefix
            if (!symbolName) continue;

            const symbol = this.symbolByName.get(symbolName);
            if (!symbol) {
                if (this.isStrict && this.grammar) {
                    throw new Error(
                        `Handler ${key} does not match any symbol; available: ${[...this.symbolByName.keys()].join(", ")}`
                    );
                }
                continue;
            }

            const method = (this as any)[key];
            if (typeof method !== "function") continue;

            // Create a handler that calls the method with named slot arguments
            const slotNames = this._getHandlerSlotNames(method);
            const handler = this._createHandler(method.bind(this), symbol, slotNames);
            this.handlerByID.set(symbol.id, handler);
        }
    }

    /** Extracts parameter names from a method (after `match`). */
    private _getHandlerSlotNames(fn: Function): string[] {
        const src = fn.toString();
        const m = src.match(/^[^(]*\(([^)]*)\)/);
        if (!m) return [];
        const params = m[1]
            .split(",")
            .map((s) => s.trim().replace(/\s*=.*$/, "").replace(/\s*:.*$/, ""))
            .filter((s) => s.length > 0);
        // First param is `match`, rest are slot names
        return params.slice(1);
    }

    /** Creates a handler wrapper that resolves named slots into positional args. */
    private _createHandler(
        method: Function,
        symbol: ParsingElement,
        slotNames: string[]
    ): ProcessorHandler {
        if (slotNames.length === 0) {
            // Simple handler: just pass the match
            return (match: Match, processor: Processor) => {
                return method(match);
            };
        }

        // Resolve slot name -> child index
        const slots: { name: string; index: number }[] = [];
        for (const name of slotNames) {
            const idx = symbol.indexForKey(name);
            if (idx < 0) {
                if (this.isStrict) {
                    throw new Error(
                        `Handler slot '${name}' not found in symbol '${symbol.name}'; available slots: ${symbol.slots().join(", ")}`
                    );
                }
                continue;
            }
            slots.push({ name, index: idx });
        }

        return (match: Match, processor: Processor) => {
            const args: unknown[] = [match];
            for (const slot of slots) {
                const child = match.get(slot.index) as Match | null;
                if (
                    !child ||
                    (child.length === 0 &&
                     child.element &&
                     child.element.type === TYPE_REFERENCE &&
                     !child.hasChildren)
                ) {
                    args.push(UNMATCHED);
                } else {
                    args.push(child);
                }
            }
            return method(...args);
        };
    }

    // -- Processing ----------------------------------------------------------

    /** Top-level entry point: processes a match tree and returns a MatchResult. */
    process(match: Match): unknown {
        // Safety: if the caller passes a non-Match value (e.g. UNMATCHED symbol,
        // a primitive, or null), return it as-is like the Python process() does.
        if (match === null || match === undefined) return null;
        if ((match as unknown) === UNMATCHED) return null;
        if (typeof match !== "object" || !(match instanceof Match)) return match as unknown;

        if (match.isFailed) {
            return UNMATCHED;
        }

        if (this.strategy === Processor.EAGER) {
            return this._processEager(match);
        }
        return this._processLazy(match);
    }

    /** Lazy processing: only processes nodes when a handler calls process()
     *  on child matches. */
    private _processLazy(match: Match): unknown {
        this.depth++;
        const result = this._dispatchMatch(match);
        this.depth--;
        const post = this.postProcess(result, match);
        return post;
    }

    /** Eager processing: bottom-up, processes all descendants first. */
    private _processEager(match: Match): unknown {
        // Process children first
        for (const child of match) {
            this._processEager(child);
        }
        this.depth++;
        const result = this._dispatchMatch(match);
        this.depth--;
        const post = this.postProcess(result, match);
        match.result = post;
        return post;
    }

    /** Dispatches a match to its handler (or default processor). */
    private _dispatchMatch(match: Match): unknown {
        // References are transparent wrappers — unwrap them before dispatch.
        // This mirrors the Python _fastProcess which never dispatches handlers
        // for Reference nodes, only for the wrapped element.
        if (match.element && match.element.type === TYPE_REFERENCE) {
            const ref = match.element as Reference;
            if (!match.hasChildren) {
                return UNMATCHED;
            }
            if (ref.isMany()) {
                // Collect all children into an array
                const result: unknown[] = [];
                let child = match.children;
                while (child) {
                    result.push(this._dispatchMatch(child));
                    child = child.next;
                }
                return result;
            } else {
                // Single child — unwrap
                return this._dispatchMatch(match.children!);
            }
        }

        const eid = match.getElementID();
        const handler = this.handlerByID.get(eid);
        if (handler) {
            return handler(match, this);
        }

        // Fall through to default type handlers
        const t = match.getType();
        switch (t) {
            case TYPE_WORD:
                return this.processWord(match);
            case TYPE_TOKEN:
                return this.processToken(match);
            case TYPE_GROUP:
                return this.processGroup(match);
            case TYPE_RULE:
                return this.processRule(match);
            case TYPE_CONDITION:
                return this.processCondition(match);
            case TYPE_PROCEDURE:
                return this.processProcedure(match);
            default:
                return this.defaultProcess(match);
        }
    }

    // -- Default type handlers (overridable) ---------------------------------

    /** Default processing when no handler matches. */
    defaultProcess(match: Match): unknown {
        if (!match.hasChildren) {
            return match.value;
        }
        const values: unknown[] = [];
        for (const child of match) {
            values.push(this.process(child));
        }
        return values.length === 1 ? values[0] : values;
    }

    processWord(match: Match): unknown {
        return match.value;
    }

    processToken(match: Match): unknown {
        return match.value;
    }

    processGroup(match: Match): unknown {
        if (match.hasChildren) {
            return this.process(match.firstChild!);
        }
        return match.value;
    }

    processRule(match: Match): unknown {
        return this.defaultProcess(match);
    }

    processCondition(_match: Match): unknown {
        return null;
    }

    processProcedure(_match: Match): unknown {
        return null;
    }

    /** Hook called after every node is processed. Override for global transforms. */
    postProcess(value: unknown, _match: Match): unknown {
        return value;
    }

    toString(): string {
        return `<Processor handlers=${this.handlerByID.size} strategy=${this.strategy === Processor.LAZY ? "LAZY" : "EAGER"}>`;
    }
}

// =============================================================================
//
// BUILT-IN CUSTOM RECOGNISERS
//
// =============================================================================

export const Recognizers = {
    /** Hand-coded recogniser for JSON strings: `"([^"\\]|\\.)*"` */
    jsonString(
        input: string,
        offset: number
    ): { length: number; groups?: string[] } | null {
        if (offset >= input.length || input[offset] !== '"') return null;
        let i = offset + 1;
        while (i < input.length) {
            const ch = input[i];
            if (ch === '"') {
                const len = i - offset + 1;
                return {
                    length: len,
                    groups: [input.slice(offset, i + 1)],
                };
            }
            if (ch === "\\") {
                i += 2; // skip escaped character
                continue;
            }
            i++;
        }
        return null; // unterminated string
    },

    /** Hand-coded recogniser for JSON numbers:
     *  `[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?` */
    jsonNumber(
        input: string,
        offset: number
    ): { length: number; groups?: string[] } | null {
        let i = offset;

        // Optional sign
        if (i < input.length && (input[i] === "+" || input[i] === "-")) i++;

        let hasDigits = false;

        // Integer part
        while (i < input.length && input[i] >= "0" && input[i] <= "9") {
            hasDigits = true;
            i++;
        }

        // Fractional part
        if (i < input.length && input[i] === ".") {
            i++;
            while (i < input.length && input[i] >= "0" && input[i] <= "9") {
                hasDigits = true;
                i++;
            }
        }

        if (!hasDigits) return null;

        // Exponent part
        if (i < input.length && (input[i] === "e" || input[i] === "E")) {
            const expStart = i;
            i++;
            if (i < input.length && (input[i] === "+" || input[i] === "-")) i++;
            let expDigits = false;
            while (i < input.length && input[i] >= "0" && input[i] <= "9") {
                expDigits = true;
                i++;
            }
            if (!expDigits) {
                // Invalid exponent, backtrack
                i = expStart;
            }
        }

        const length = i - offset;
        if (length === 0) return null;
        return { length, groups: [input.slice(offset, i)] };
    },
};

// =============================================================================
//
// UTILITIES (private)
//
// =============================================================================

/** Counts newline characters in `input[start..end)`. */
function _countNewlines(input: string, start: number, end: number): number {
    let count = 0;
    for (let i = start; i < end; i++) {
        if (input.charCodeAt(i) === 10) count++;
    }
    return count;
}

/** Escapes a string for use in XML attribute values. */
function _xmlEscape(s: string): string {
    return s
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

/** High-resolution timer (milliseconds). */
function _now(): number {
    if (typeof performance !== "undefined" && performance.now) {
        return performance.now();
    }
    return Date.now();
}
