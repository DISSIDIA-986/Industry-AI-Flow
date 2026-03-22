/**
 * Golden Questions — curated questions for Workflow Chat, organized by document category.
 * Based on Jack's 6 priority documents from the construction knowledge base.
 *
 * Each primary question (first in each category) has static follow-up chains
 * for the demo's 5-round conversation flow.
 */

export interface GoldenQuestion {
  text: string;
  /** Static follow-ups for the first response to this question (primary questions only) */
  followUps?: string[];
}

export interface DocumentCategory {
  id: string;
  label: string;
  /** Short label for compact display */
  shortLabel: string;
  /** Color dot class (Tailwind) */
  dotColor: string;
  /** Category type for grouping */
  type: "code" | "safety" | "contract";
  questions: GoldenQuestion[];
}

export const GOLDEN_QUESTIONS: DocumentCategory[] = [
  {
    id: "nbc-2020",
    label: "National Building Code (NBC) 2020",
    shortLabel: "NBC 2020",
    dotColor: "bg-blue-500",
    type: "code",
    questions: [
      {
        text: "What are the five stated objectives of the National Building Code of Canada?",
        followUps: [
          "How do these objectives translate into specific compliance requirements for residential construction?",
          "Which NBC objective most directly impacts fire safety design decisions?",
          "Create a pre-construction compliance checklist based on these five objectives.",
        ],
      },
      {
        text: "How does the NBC define 'fire compartment' and what fire-resistance rating is required?",
      },
      {
        text: "Under the NBC, when can separate portions of a building be treated as separate buildings?",
      },
    ],
  },
  {
    id: "ontario-reg",
    label: "Ontario Reg. 213/91 (Construction Projects)",
    shortLabel: "Ontario Reg. 213/91",
    dotColor: "bg-green-500",
    type: "safety",
    questions: [
      {
        text: "What is the ranked hierarchy of fall protection methods required under Ontario Regulation 213/91?",
        followUps: [
          "What specific training requirements does Ontario Regulation 213/91 mandate for workers using each fall protection method?",
          "Compare the fall protection requirements between Ontario Regulation 213/91 and federal OHS regulations.",
          "Create a site safety inspection checklist for fall protection compliance under Ontario Regulation 213/91.",
        ],
      },
      {
        text: "What personal protective equipment must a worker wear on an Ontario construction project?",
      },
      {
        text: "What notification must a constructor file before beginning a construction project under Ontario Reg 213/91?",
      },
    ],
  },
  {
    id: "canada-ohs",
    label: "Canada OHS Regulations (SOR/86-304)",
    shortLabel: "Canada OHS",
    dotColor: "bg-green-500",
    type: "safety",
    questions: [
      {
        text: "What are the employer obligations for workplace hazard prevention under the Canada OHS Regulations?",
        followUps: [
          "What specific hazardous substances are regulated under SOR/86-304 and what exposure limits apply?",
          "How do federal OHS requirements interact with provincial workplace safety laws on construction sites?",
          "Create a compliance checklist for employer obligations under Canada OHS Regulations.",
        ],
      },
      {
        text: "What training requirements does SOR/86-304 mandate for workers handling hazardous substances?",
      },
    ],
  },
  {
    id: "bc-code",
    label: "BC Building Code 2024",
    shortLabel: "BC Code 2024",
    dotColor: "bg-blue-500",
    type: "code",
    questions: [
      {
        text: "What are the key changes in the BC Building Code 2024 compared to previous editions?",
        followUps: [
          "How do the energy efficiency standards in BC Building Code 2024 compare with the National Building Code?",
          "What structural design requirements does the BC Building Code 2024 mandate for seismic zones?",
          "Summarize the accessibility requirements in the BC Building Code 2024 for commercial buildings.",
        ],
      },
      {
        text: "What energy efficiency standards does the BC Building Code 2024 mandate for commercial buildings?",
      },
    ],
  },
  {
    id: "quebec-safety",
    label: "Quebec Safety Code (S-2.1, r. 4)",
    shortLabel: "Quebec Safety",
    dotColor: "bg-green-500",
    type: "safety",
    questions: [
      {
        text: "How do Quebec's construction safety requirements differ from federal OHS regulations?",
        followUps: [
          "What specific fall protection standards does Quebec Safety Code mandate for construction sites?",
          "What are the enforcement mechanisms and penalties under Quebec's construction safety code?",
          "Compare scaffolding safety requirements between Quebec Safety Code and Ontario Regulation 213/91.",
        ],
      },
      {
        text: "What are the key worker safety obligations specific to Quebec construction projects under S-2.1, r. 4?",
      },
    ],
  },
  {
    id: "labour-code",
    label: "Canada Labour Code Part II",
    shortLabel: "Labour Code II",
    dotColor: "bg-amber-500",
    type: "contract",
    questions: [
      {
        text: "What are the key employee rights under Part II of the Canada Labour Code regarding workplace safety?",
        followUps: [
          "How does the right to refuse dangerous work operate under the Canada Labour Code?",
          "What role do workplace health and safety committees play under the Canada Labour Code Part II?",
          "Create a summary of employer vs employee responsibilities under Canada Labour Code Part II.",
        ],
      },
      {
        text: "How does the Canada Labour Code Part II handle workplace hazard reporting and investigation?",
      },
    ],
  },
];

/** Total number of questions across all categories */
export const TOTAL_QUESTIONS = GOLDEN_QUESTIONS.reduce(
  (sum, cat) => sum + cat.questions.length,
  0,
);

/** Total number of document categories */
export const TOTAL_DOCUMENTS = GOLDEN_QUESTIONS.length;

/**
 * Find static follow-ups for a given question text.
 * Returns undefined if the question has no curated follow-ups (secondary questions).
 */
export function getStaticFollowUps(questionText: string): string[] | undefined {
  for (const category of GOLDEN_QUESTIONS) {
    for (const q of category.questions) {
      if (q.text === questionText && q.followUps) {
        return q.followUps;
      }
    }
  }
  return undefined;
}
