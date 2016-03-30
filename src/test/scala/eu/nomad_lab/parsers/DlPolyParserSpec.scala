package eu.nomad_lab.parsers

import org.specs2.mutable.Specification

object DlPolyParserSpec extends Specification {
  "DlPolyParserTest" >> {
    "test with json-events" >> {
      ParserRun.parse(DlPolyParser, "parsers/dl-poly/test/examples/dl-poly-test1/OUTPUT", "json-events") must_== ParseResult.ParseSuccess
    }
    "test with json" >> {
      ParserRun.parse(DlPolyParser, "parsers/dl-poly/test/examples/dl-poly-test1/OUTPUT", "json") must_== ParseResult.ParseSuccess
    }
  }
}
