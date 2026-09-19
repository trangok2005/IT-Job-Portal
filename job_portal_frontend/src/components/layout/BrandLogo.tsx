import Image from "next/image";

import logo from "../../../public/logo.png";
import { cn } from "@/lib/utils";

export function BrandLogo({ className }: { className?: string }) {
  return (
    <Image
      src={logo}
      alt="Semantic-Job-Platform"
      className={cn(
        "size-16 rounded-full border-2 border-primary/15 object-cover shadow-sm",
        className,
      )}
      priority
    />
  );
}
