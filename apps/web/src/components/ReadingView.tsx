import { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMermaid from "remark-mermaid-plugin";
import rehypeHighlight from "rehype-highlight";
import rehypeRaw from "rehype-raw";

interface ReadingViewProps {
  content: string;
}

const ReadingView = ({ content }: ReadingViewProps) => {
  // This component is wrapped in React.memo to prevent unnecessary re-renders.
  // The markdown rendering is computationally expensive, so we only want to
  // re-render when the `content` prop actually changes.
  return (
    <div className="reading">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMermaid as any]}
        rehypePlugins={[rehypeHighlight, rehypeRaw]}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default memo(ReadingView);
